#!/usr/bin/env python3
import gi       # type: ignore
import sys

import gimp_utils
import sd_api

gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gtk', '3.0')

from gi.repository import Gimp, GimpUi, Gtk, GLib, GObject

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

class StableDiffusionPlugin (Gimp.PlugIn):
    style_list = []

    def do_query_procedures(self):
        return [ 
            "text-to-image",
            "image-to-image",
            "upscale",
            "remove-background"
        ]
    
    def do_set_i18n(self, name):
        # Support language translation.
        return False, None, None
    
    def init_procedure(self, name, procedure):
        procedure.set_image_types("*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)

        procedure.set_menu_label(_(name.replace('-', ' ').title()))
        procedure.set_icon_name(GimpUi.ICON_GEGL)
        procedure.add_menu_path('<Image>/StableDiffusion/')

        procedure.set_documentation(_("Gimp hook for Automatic1111 Stable Diffusion WebUI"),
                                        _("Gimp hook for Automatic1111 Stable Diffusion WebUI"),
                                        name)
        procedure.set_attribution("Stygian", "Stygian", "2024")

    def do_create_procedure(self, name):
        if name in ["text-to-image", "image-to-image"]:
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                self.run_generation, None)

            self.init_procedure(name, procedure)

            procedure.add_string_argument('prompt', 'Positive prompt', 'Positive prompt for image generation', '', GObject.ParamFlags.READWRITE)
            procedure.add_string_argument('negative_prompt', 'Negative prompt', 'Negative prompt for image generation', '', GObject.ParamFlags.READWRITE)

            for style in sd_api.get_styles():
                procedure.add_boolean_argument(style['name'], style['name'], '+\t%s \n-\t%s' % (style['prompt'], style['negative_prompt']), False, GObject.ParamFlags.READWRITE)
                self.style_list.append(style['name'])

            procedure.add_int_argument('steps', 'Steps', 'Number of steps', 5, 100, 12, GObject.ParamFlags.READWRITE)
            procedure.add_int_argument('n_iter', 'Batch count', 'Number of batches', 1, 10, 1, GObject.ParamFlags.READWRITE)
            procedure.add_int_argument('batch_size', 'Batch size', 'Number of pictures in a batch', 1, 50, 1, GObject.ParamFlags.READWRITE)

            models = Gimp.Choice()
            id = 0
            for model in sd_api.get_models():
                id += 1
                models.add(model['title'], id, model['model_name'], '')
            procedure.add_choice_argument('model', 'Checkpoint', 'Checkpoint', models, sd_api.get_current_model(), GObject.ParamFlags.READWRITE)

            samplers = Gimp.Choice()
            id = 0
            for sampler in sd_api.get_samplers():
                id += 1
                samplers.add(sampler['name'], id, sampler['name'], '')
            procedure.add_choice_argument('sampler_name', 'Sampler', 'Sampler', samplers, "Euler a", GObject.ParamFlags.READWRITE)

            procedure.add_double_argument('cfg_scale', 'CFG Scale', 'Classifier Free Guidance Scale - how strongly the image should conform to prompt - lower values produce more creative results', 1, 20, 6, GObject.ParamFlags.READWRITE)

            procedure.add_int_argument('seed', 'Seed', 'Generation seed', -999999, 999999, -1, GObject.ParamFlags.READWRITE)

            cn_models = Gimp.Choice()
            id = 0
            for model in sd_api.get_controlnet_models():
                id += 1
                cn_models.add(model, id, model, '')
            procedure.add_choice_argument('controlnet_model', 'ControlNet Model', 'ControlNet Model', cn_models, "Euler a", GObject.ParamFlags.READWRITE)

            if name != 'text-to-image':
                procedure.add_double_argument('denoising_strength', 'Denoising strength', "Determines how little respect the algorithm should have for image's content. At 0, nothing will change, and at 1 you'll get an unrelated image. With values below 1.0, processing will take less steps than the Sampling Steps slider specifies.", 0, 1, 0.5, GObject.ParamFlags.READWRITE)
                procedure.add_drawable_argument('mask', 'Inpainting mask', 'Layer used as a mask for Inpainting. Black areas should be the zone that will be inpainted, white or transparent will not be inpainted.', True, GObject.ParamFlags.READWRITE)
               
                inpainting_modes = Gimp.Choice()
                id = 0
                for mode in ['fill', 'original', 'latent-nothing', 'latent-noise']:
                    inpainting_modes.add(str(id + 1), id, mode, '')
                    id += 1
                
                procedure.add_choice_argument('inpainting_fill', 'Fill with', 'Fill inpainted area with', inpainting_modes, "0", GObject.ParamFlags.READWRITE)
        elif name == "upscale":
            procedure = Gimp.ImageProcedure.new(self, name,
                                    Gimp.PDBProcType.PLUGIN,
                                    self.run_upscale, None)

            self.init_procedure(name, procedure)
            
            procedure.add_double_argument('upscaling_resize', 'Upscale by', 'Multiplier applied to image size', 1, 10, 2, GObject.ParamFlags.READWRITE)
            upscaler_models = Gimp.Choice()
            id = 0
            for model in sd_api.get_upscaler_models():
                id += 1
                upscaler_models.add(model['name'], id, model['name'], '')

            procedure.add_choice_argument('upscaler_1', 'Upscaler 1', 'First upscaler model used', upscaler_models, 'None', GObject.ParamFlags.READWRITE)
            procedure.add_choice_argument('upscaler_2', 'Upscaler 2', 'Second upscaler model used', upscaler_models, 'None', GObject.ParamFlags.READWRITE)
            procedure.add_double_argument('extras_upscaler_2_visibility', 'Upscaler 2 visibility', 'Weight of the second upscaler', 0, 1, 0, GObject.ParamFlags.READWRITE)
        else:
            procedure = Gimp.ImageProcedure.new(self, name,
                                    Gimp.PDBProcType.PLUGIN,
                                    self.run_remove_bg, None)

            self.init_procedure(name, procedure)
            
            rembg_models = Gimp.Choice()
            id = 0
            for model in sd_api.get_rembg_models():
                id += 1
                rembg_models.add(model, id, model, '')

            procedure.add_choice_argument('model', 'Model', 'Remove background model', rembg_models, 'None', GObject.ParamFlags.READWRITE)
            procedure.add_boolean_argument('return_mask', 'Return mask', 'Returns used mask instead of foreground', False, GObject.ParamFlags.READWRITE)
            procedure.add_boolean_argument('alpha_matting', 'Alpha matting', 'Alpha matting is a post processing step that can be used to improve the quality of the output.', False, GObject.ParamFlags.READWRITE)

            procedure.add_int_argument('alpha_matting_erode_size', 'Erode size', 'Erode size', 1, 40, 10, GObject.ParamFlags.READWRITE)
            procedure.add_int_argument('alpha_matting_foreground_threshold', 'Foreground threshold', 'Foreground threshold', 0, 255, 240, GObject.ParamFlags.READWRITE)
            procedure.add_int_argument('alpha_matting_background_threshold', 'Background threshold', 'Background threshold', 0, 255, 10, GObject.ParamFlags.READWRITE)
        
        return procedure
    
    def get_config(self, config):
        config_data = {}

        for property in dir(config.props):
            if property != 'procedure':
                config_data[property] = config.get_property(property)

        return config_data

    def run_remove_bg(self, procedure, run_mode, image, drawables, config, run_data):
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init( "sd_plugin.py" )

            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)

            dialog.get_widget('alpha_matting_erode_size', GimpUi.ScaleEntry)
            dialog.get_widget('alpha_matting_foreground_threshold', GimpUi.ScaleEntry)
            dialog.get_widget('alpha_matting_background_threshold', GimpUi.ScaleEntry)

            dialog.fill_box('alpha-list', ['alpha_matting_erode_size','alpha_matting_foreground_threshold','alpha_matting_background_threshold'])
            dialog.fill_expander('alpha_matting_expander', 'alpha_matting', False, 'alpha-list')

            dialog.fill(['model', 'return_mask', 'alpha_matting_expander'])

            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error()
                )
            else:
                dialog.destroy()

            config_data = self.get_config(config)
            config_data["input_image"] = gimp_utils.get_image_as_base64(image)

            generated_image = sd_api.remove_bg(config_data)
            gimp_utils.load_base64_image(generated_image, image)

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    def run_upscale(self, procedure, run_mode, image, drawables, config, run_data):
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init( "sd_plugin.py" )

            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)

            dialog.get_widget('upscaling_resize', GimpUi.ScaleEntry).set_digits(1)
            dialog.get_widget('extras_upscaler_2_visibility', GimpUi.ScaleEntry).set_digits(2)

            dialog.fill()

            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error()
                )
            else:
                dialog.destroy()

            config_data = self.get_config(config)
            config_data["image"] = gimp_utils.get_image_as_base64(image)

            generated_image = sd_api.upscale(config_data)
            gimp_utils.load_base64_image(generated_image, image)
            image.resize_to_layers()

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
    
    def run_generation(self, procedure, run_mode, image, drawables, config, run_data):
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init( "sd_plugin.py" )

            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)

            dialog.get_label('prompt-label', 'Positive prompt', False, False).set_halign(Gtk.Align.START)
            dialog.get_widget('prompt', Gtk.TextView)
            dialog.get_label('negative-prompt-label', 'Negative prompt', False, False).set_halign(Gtk.Align.START)
            dialog.get_widget('negative_prompt', Gtk.TextView).set_margin_bottom(10)

            dialog.get_label('style-label', 'Styles', False, False)
            flowbox = dialog.fill_flowbox('style-list', self.style_list)
            flowbox.set_max_children_per_line(3)
            expander = dialog.fill_expander('styles', 'style-label', False, 'style-list')
            expander.set_expanded(True)

            prompt_fields = ['prompt-label', 'prompt', 'negative-prompt-label', 'negative_prompt', 'styles']

            if procedure.get_name() != 'text-to-image':
                dialog.get_widget('denoising_strength', GimpUi.ScaleEntry).set_digits(2)
                prompt_fields.append('denoising_strength')

                dialog.get_label('inpainting-label', 'Inpainting', False, False)

                dialog.fill_box('inpainting-list', ['mask', 'inpainting_fill'])

                expander = dialog.fill_expander('inpainting-options', 'inpainting-label', False, 'inpainting-list')
                expander.set_expanded(False)
                
                prompt_fields.append('inpainting-options')

            dialog.fill_box('prompt-options', prompt_fields)

            dialog.get_widget('steps', GimpUi.ScaleEntry)

            flowbox = dialog.fill_flowbox('batch-list', ['n_iter', 'batch_size'])
            flowbox.set_valign(Gtk.Align.START)
            flowbox.set_min_children_per_line(2)

            dialog.get_label('generation-label', 'Generation options', False, False)
            dialog.get_widget('cfg_scale', GimpUi.ScaleEntry).set_digits(1)
            dialog.fill_box('generation-list', ['model', 'sampler_name', 'cfg_scale'])
            expander = dialog.fill_expander('generation-options', 'generation-label', False, 'generation-list')
            expander.set_expanded(True)
            dialog.get_widget('model', GObject.TYPE_NONE).set_margin_top(10)

            dialog.get_label('advanced-label', 'Advanced options', False, False)
            dialog.fill_box('advanced-list', ['seed'])
            expander = dialog.fill_expander('advanced-options', 'advanced-label', False, 'advanced-list')
            dialog.get_widget('seed', GObject.TYPE_NONE).set_margin_top(10)

            dialog.fill(['prompt-options', 'steps', 'batch-list', 'generation-options', 'advanced-options'])

            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error()
                )
            else:
                dialog.destroy()

            styles = []
            for style in self.style_list:
                if config.get_property(style):
                    styles.append(style)

            success, non_empty, x1, y1, x2, y2 = Gimp.Selection.bounds(image)

            config_data = self.get_config(config) | {
                "width": abs(x1 - x2) if non_empty else image.get_width(),
                "height": abs(y1 - y2) if non_empty else image.get_height(),
                "styles": styles,
                "override_settings": {"sd_model_checkpoint": config.get_property('model')},
            }

            match procedure.get_name():
                case 'text-to-image':
                    generated_images = sd_api.txt_to_img(config_data)
                case 'image-to-image':
                    inpainting_mask = config_data['mask']

                    if inpainting_mask:
                        copied_mask = gimp_utils.copy_layer(image, inpainting_mask)
                        config_data['mask'] = gimp_utils.get_image_as_base64(image)
                        image.remove_layer(copied_mask)
                        inpainting_mask.set_visible(False)

                    config_data["init_images"] = [gimp_utils.get_image_as_base64(image)]

                    if inpainting_mask: inpainting_mask.set_visible(True)

                    generated_images = sd_api.img_to_img(config_data)
            
            i = -1
            for base64_image in generated_images:
                i += 1
                if i == 0 and len(generated_images) > 1:
                    continue

                gimp_utils.load_base64_image(base64_image, image)

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

Gimp.main(StableDiffusionPlugin.__gtype__, sys.argv)
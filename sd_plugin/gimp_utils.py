#!/usr/bin/env python3
import gi 
gi.require_version('Gimp', '3.0')

from gi.repository import Gimp, Gio
import base64

def get_image_as_base64(image):
    #image = copy_image(image)

    procedure = Gimp.get_pdb().lookup_procedure('file-png-export'); 
    config = procedure.create_config(); 
    config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE); 
    config.set_property('image', image); 
    file = Gio.File.new_tmp()[0]

    config.set_property('file', file); 
    config.set_property('options', None);
    config.set_property('format', 'auto');
    result = procedure.run(config); 
    success = result.index(0)

    with open(file.get_path(), 'rb') as file:
        return base64.b64encode(file.read()).decode("utf-8")

def copy_layer(image, layer):
    layer = layer.copy()
    image.insert_layer(layer, None, 0)
    layer.flatten()
    layer.set_opacity(100)

    return layer

def load_base64_image(base64_img, image):
    file, stream = Gio.File.new_tmp()
    stream.get_output_stream().write(base64.b64decode(base64_img), None)
    stream.close()

    load_file_in_layer(image, file)

def load_file_in_layer(image, file):
    layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, file)
    selection_pos = Gimp.Selection.bounds(image)
    layer.set_offsets(selection_pos.x1, selection_pos.y1)

    image.insert_layer(layer, None, 0)
    image.resize_to_layers()
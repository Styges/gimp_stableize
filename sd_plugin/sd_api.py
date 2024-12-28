#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
import threading
import gi       # type: ignore

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

SD_BASE_URL = "http://127.0.0.1:7860/"
SD_API_URL = SD_BASE_URL + "sdapi/v1/"

BASE_CONFIG = {
    "save_images": True
}

def get_list_from_api(uri, param_name):
    list = []

    for element in get_request(uri):
        list.append(element[param_name])

    return list

def get_models():
    return get_list_from_api("sd-models", "title")

def get_upscaler_models():
    return get_list_from_api("upscalers", "name")

def get_latent_upscale_modes():
    return get_list_from_api("latent-upscale-modes", "name")

def get_samplers():
    return get_list_from_api("samplers", "name")

def get_schedulers():
    return get_list_from_api("schedulers", "label")

def get_rembg_models():
    #Hardcoded in base module, not accessible by API
    return [    
        "None",
        "isnet-general-use",
        "isnet-anime",
        "u2net",
        "u2netp",
        "u2net_human_seg",
        "u2net_cloth_seg",
        "silueta"
    ]

def get_controlnet_models():
    return get_request("controlnet/model_list", SD_BASE_URL)["model_list"]

def get_controlnet_modules():
    return get_request("controlnet/module_list", SD_BASE_URL)["module_list"]

def get_current_model():
    return get_request("options")["sd_model_checkpoint"]

def get_styles():
    return get_request("prompt-styles")

def get_request(uri, base_url = SD_API_URL):
    with urlopen(base_url + uri) as response:
        return json.loads(response.read())
    
def txt_to_img(config_data):
    response = post_request("txt2img", config_data | BASE_CONFIG)
    
    return response["images"]

def img_to_img(config_data):
    response = post_request("img2img", config_data | BASE_CONFIG)

    return response["images"]

def upscale(config_data):
    response = post_request("extra-single-image", config_data)

    return response["image"]

def remove_bg(config_data):
    response = post_request("rembg", config_data, SD_BASE_URL)

    return response["image"]

def post_request(uri, data: dict, base_url = SD_API_URL):
    request = Request(
        base_url + uri,
        data = json.dumps(data).encode(),
        headers = {"Content-Type": "application/json"}
    )

    thread = threading.Thread(target=create_progress_bar)
    thread.start()

    with urlopen(request) as response:
        thread.join()
        return json.loads(response.read())

def create_progress_bar():
    progress = ProgressBar()
    progress.run()

class ProgressBar(Gtk.Application):

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Generation progress")
        self.progress = Gtk.ProgressBar(show_text=True)

        window.set_border_width(20)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        vbox.pack_start(self.progress, True, True, 0)

        window.present()
        window.show_all()

        self.timeout_id = GLib.timeout_add(100, self.on_timeout, None)

    def on_timeout(self, user_data):
        progress_json = get_request("progress")
        progress = progress_json["progress"]

        if progress > 0:
            self.progress.set_fraction(progress)
            self.progress.set_text("%s - ETA: %ss" % (progress_json["state"]["job"], f"{max(progress_json["eta_relative"], 0):.2f}"))
        
            return True
    
        self.quit()
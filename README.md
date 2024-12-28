# Gimp Stableize
Gimp 3.0 (RC1) Plugin for A1111 StableDiffusion WebUI

The goal of this plugin is to make all the main features present in https://github.com/AUTOMATIC1111/stable-diffusion-webui available directly in GIMP 3.0 (RC1).
This plugin requires a running A1111 WebUI with argument --api *before* GIMP is opened. This is because all the informations about models, styles, samplers and extra models are queried directly from the API. If you fail to do so before opening GIMP for the first time after you installed this plugin, most of the features will be missing in the menu. To fix this, delete your GIMP pluginrc file and try again.

WIP:
Hires-fix
Refiner
Extra networks
Outpainting
Control Net

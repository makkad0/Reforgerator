import numpy as np
from PIL import Image
import external.pytoshop as pytoshop
import external.pytoshop.codecs
from external.pytoshop.user import nested_layers
from external.pytoshop.enums import ColorChannel, ChannelId

OPACITY_MAX=255

def psd_path_to_pil(psd_path):
    pil_image = None
    try:
        # Open and read the PSD file
        with open(psd_path, 'rb') as f:
            psd = pytoshop.read(f)
            # Convert PSD to nested layers
            psd_layers = nested_layers.psd_to_nested_layers(psd)
            pil_image = merge_psd_layers_to_pil(psd_layers)
    except Exception as e:
        print(e)
        pil_image = Image.open(psd_path)
    return pil_image


def merge_psd_layers_to_pil(layers):
    # Process each top-level layer
    composite_image = None
    for layer in layers:
        layer_image = process_layer(layer)
        if layer_image:
            if composite_image:
                composite_image = Image.alpha_composite(layer_image,composite_image)
            else:
                composite_image = layer_image
    return composite_image

def get_channel_data(channel):
    # Attempt to retrieve raw channel data from a ChannelImageData object.
    if hasattr(channel, 'image'):
        return channel.image
    else:
        return None


def process_layer(layer):
    if isinstance(layer, nested_layers.Group):
        for sublayer in layer.layers:
            process_layer(sublayer)
    elif isinstance(layer, nested_layers.Image):
        opacity=OPACITY_MAX
        if hasattr(layer, 'visible'):
            if not layer.visible:
                return None
        if hasattr(layer, 'opacity'):
            opacity=layer.opacity
        channel_mask_array = None
        channel_alpha_array = None
        channel_arrays = []
        channel_id_set = [ColorChannel.red, ColorChannel.green, ColorChannel.blue,ChannelId.transparency,ChannelId.user_layer_mask]
        for channel_id in channel_id_set:
            try:
                channel = layer.get_channel(channel_id)
            except Exception as e:
                channel = None
            if channel is not None:
                raw = get_channel_data(channel)
                ch_height, ch_width = raw.shape
                # Create a numpy array from raw bytes
                arr = np.frombuffer(raw, dtype=np.uint8).reshape((ch_height, ch_width))
                if channel_id==ChannelId.user_layer_mask:
                    channel_mask_array=arr
                elif channel_id==ChannelId.transparency:
                    channel_alpha_array=arr
                else:
                    channel_arrays.append(arr)
        if channel_arrays:
            # # Stack RGB channels along the last axis
            image_array = np.stack(channel_arrays, axis=-1)

            if channel_alpha_array is not None:
                # If an alpha channel exists, use it; otherwise, create a fully opaque alpha channel
                alpha_channel = channel_alpha_array
            else:
                alpha_channel = np.full((ch_height, ch_width), OPACITY_MAX, dtype=np.uint8)
            
            if channel_mask_array is not None:
                # Combine the mask with the alpha channel
                alpha_channel = (alpha_channel.astype(np.float32) * (channel_mask_array.astype(np.float32) / OPACITY_MAX)).astype(np.uint8)
            
            # Apply layer opacity
            if opacity < OPACITY_MAX:
                alpha_channel = (alpha_channel.astype(np.float32) * (opacity / OPACITY_MAX)).astype(np.uint8)

            # Add the alpha channel to the image array
            image_array = np.dstack((image_array, alpha_channel))

            # Create a PIL image from the array.
            pil_image = Image.fromarray(image_array)

            return pil_image
    return None
import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import external.jpgwrapper as jpgw
from PIL import Image
import numpy as np
import json
from blp1_utils import parse_jpeg_markers 

def save_as_jpeg_and_anylize(input_path,output_folder):

    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # Open the PNG image using Pillow
    img = Image.open(input_path)

    # Ensure the image is in RGB mode (simplejpeg expects RGB for typical images)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 3. Convert image to NumPy array (shape: height x width x 4)
    rgba = np.array(img)

    # 4. Convert from RGBA to BGRA by swapping the R and B channels
    bgra = rgba[..., [2, 1, 0, 3]]  # new order: B, G, R, A

    # 5. Flatten the array to create a contiguous bytes buffer
    bgra_bytes = bgra.tobytes()

    # Get image dimensions
    width, height = img.size

    # Set JPEG quality and bottom-up flag (set bottomUp to False for top-down image order)
    quality = 85
    bottomUp = False

    # 6. Call the compress_bgra_to_jpeg function.
    #    It expects: image_buffer (bytes), buffer_length, width, height, quality, [bottomUp]
    jpeg_bytes = jpgw.compress_bgra_to_jpeg(bgra_bytes, width, height, quality, True)

    # Save the resulting JPEG bytes to a file

    output_path = os.path.join(output_folder,base_name+ ".jpg")

    with open(output_path, "wb") as f:
        f.write(jpeg_bytes)

    #Analyze_jpeg_file
    markers, total_bytes = parse_jpeg_markers(output_path)
    output_data = {
        "file": input_name,
        "total_bytes": total_bytes,
        "markers": markers
    }
    output_file_path_json=os.path.join(output_folder,base_name+".jpg.json")

    with open(output_file_path_json, 'w') as f:
        json.dump(output_data, f, indent=4)
        print(f"JSON output written to {output_file_path_json}")

if __name__ == "__main__":
    input_name="input.png"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = "tempoutput"
    output_dir_path=os.path.join(script_dir,output_dir)
    input_dir = "tempinput"
    input_dir_path=os.path.join(script_dir,input_dir)
    input_file_path=os.path.join(input_dir_path,input_name)
    save_as_jpeg_and_anylize(input_file_path,output_dir_path)


    
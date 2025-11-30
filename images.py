import io

from PIL import Image, ImageDraw, ImageFont


def generate_avatar(username: str):
    img = Image.new('RGB', (256, 256), color='black')

    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype('arial.ttf', size=256)

    draw.text((100, 0), username[0], fill='white', font=font)

    byte_arr = io.BytesIO()
    img.save(byte_arr, format='PNG')
    byte_data = byte_arr.getvalue()
    return byte_data

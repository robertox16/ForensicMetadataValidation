from PIL import Image, ImageChops, ImageEnhance
import io, base64

def compute_ela_img(original, compressed, scale=5):
    diff = ImageChops.difference(original, compressed)
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema]) or 1
    factor = 255.0 / max_diff * scale
    return ImageEnhance.Brightness(diff).enhance(factor)

def pil_to_datauri(img, fmt="JPEG"):
    buf = io.BytesIO()
    img.save(buf, fmt)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/{fmt.lower()};base64,{b64}"

def generate_ela_datauris(image_path, quality_high=95, quality_low=10, scale=5):
    original = Image.open(image_path).convert("RGB")
    # versiones recomprimidas
    buf_hq = io.BytesIO()
    buf_lq = io.BytesIO()
    original.save(buf_hq, "JPEG", quality=quality_high)
    original.save(buf_lq, "JPEG", quality=quality_low)
    hq = Image.open(io.BytesIO(buf_hq.getvalue()))
    lq = Image.open(io.BytesIO(buf_lq.getvalue()))
    # ELA
    ela_hq = compute_ela_img(original, hq, scale)
    ela_lq = compute_ela_img(original, lq, scale)
    # Data URIs
    return {
        "original": pil_to_datauri(original, "PNG"),
        f"hq_{quality_high}": pil_to_datauri(hq),
        f"lq_{quality_low}": pil_to_datauri(lq),
        f"ela_hq_{quality_high}": pil_to_datauri(ela_hq),
        f"ela_lq_{quality_low}": pil_to_datauri(ela_lq),
    }

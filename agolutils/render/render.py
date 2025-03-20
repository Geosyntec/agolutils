from pathlib import Path

from docx.shared import Inches, Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2.exceptions import TemplateSyntaxError
from PIL import Image, ImageOps

from agolutils.config.config import load_config
from agolutils.context.context import load_context
from agolutils.utils import get_plugin, make_path

UNITS = {
    "inches": Inches,
    "inch": Inches,
    "in": Inches,
    "millimeters": Mm,
    "millimeter": Mm,
    "mm": Mm,
}


def render_docx_template(
    context,
    config=None,
    template=None,
    report_file=None,
    report_file_pattern=None,
) -> Path:
    config = load_config(config)
    context = load_context(context)

    plugin = get_plugin(config)
    context, config = plugin(context, config)

    _config_report_pattern = config.get("report_file_pattern")
    if report_file_pattern is None and _config_report_pattern:
        report_file = Path(config["__config_relpath"]) / _config_report_pattern.format(
            **context
        )

    if template is None:
        _config_template = config.get("docxtpl", {})["template_filepath"]
        template = Path(config["__config_relpath"]) / _config_template

    doc = DocxTemplate(template)
    context = parse_docx_images(doc, config, context)
    output = make_path(report_file)

    jinja_env = context.pop("_jinja_env", None)
    autoescape = context.pop("_autoescape", False)

    try:
        doc.render(context, jinja_env=jinja_env, autoescape=autoescape)

    except TemplateSyntaxError as e:
        line = str(e.source).splitlines()[e.lineno - 1]
        raise ValueError(
            f"Template Syntax Error: {e.message}\n\t"
            f"line no.: {e.lineno - 1}\n\tsource: {line}"
        ) from e

    doc.save(output)

    return output


def build_docx_image(template, info, context):
    key = info.get("key")
    if not key or key not in context:
        return context

    if isinstance(context[key], dict):
        images = [context[key]]
    elif isinstance(context[key], list):
        images = context[key]
    else:
        return context

    if not images:
        return context

    filepath_key = info["filepath_key"]
    unit_key = info["units"].lower()
    units = UNITS.get(unit_key, Inches)
    max_w = info.get("max-width", None)
    max_h = info.get("max-height", None)

    for image_dict in images:
        path = context["__context_relpath"] / Path(image_dict[filepath_key])
        width = None
        height = None

        with ImageOps.exif_transpose(Image.open(path)) as image:
            # gotta get the actual size of the image to know how to constrain it.

            image.save(path)

            w, h = image.size

            if max_w and w > h:
                width = units(max_w)
            elif max_h:
                height = units(max_h)

        image_dict["docxtpl_image"] = InlineImage(
            template, image_descriptor=str(path), width=width, height=height
        )

    return context


def parse_docx_images(template, config, context):
    docx_photo_info = config.get("docxtpl", {}).get("image", [])

    for info in docx_photo_info:
        context = build_docx_image(template, info, context)

    return context


def parse_subdocs(template, config, context):
    _ = config.get("subdocs", {})
    _ = template

    return context

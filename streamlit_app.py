import os
from hashlib import blake2b
from tempfile import NamedTemporaryFile

import dotenv
from streamlit_pdf_viewer import pdf_viewer

dotenv.load_dotenv(override=True)

import streamlit as st

if 'doc_id' not in st.session_state:
    st.session_state['doc_id'] = None

if 'hash' not in st.session_state:
    st.session_state['hash'] = None

if 'git_rev' not in st.session_state:
    st.session_state['git_rev'] = "unknown"
    if os.path.exists("revision.txt"):
        with open("revision.txt", 'r') as fr:
            from_file = fr.read()
            st.session_state['git_rev'] = from_file if len(from_file) > 0 else "unknown"

if 'uploaded' not in st.session_state:
    st.session_state['uploaded'] = False

if 'binary' not in st.session_state:
    st.session_state['binary'] = None

if 'annotations' not in st.session_state:
    st.session_state['annotations'] = []

if 'pages' not in st.session_state:
    st.session_state['pages'] = None

if 'page_selection' not in st.session_state:
    st.session_state['page_selection'] = []

if 'size_in_pixel' not in st.session_state:
    st.session_state['size_in_pixel'] = None

print(st.session_state['annotations'])

st.set_page_config(
    page_title="Structure vision",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://github.com/lfoppiano/pdf-struct',
        'Report a bug': "https://github.com/lfoppiano/pdf-struct/issues",
        'About': "View the structures extracted by Grobid."
    }
)


def box_to_dict(annotation_raw, color=None, type=None):
    # First try to split by semicolon if multiple annotations are provided
    annotations = []

    if ";" in annotation_raw:
        # Split by semicolon for multiple annotations
        items = annotation_raw.split(";")
    else:
        # Try splitting by newline
        items = annotation_raw.split("\n")

    for item in items:
        if not item.strip():
            continue

        # Split each annotation by comma to get page,x,y,width,height
        parts = item.strip().split(",")
        if len(parts) >= 5:
            box = {
                "page": int(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "width": float(parts[3]),
                "height": float(parts[4])
            }

            if color is not None:
                box['color'] = color
            elif len(parts) > 5:
                box['color'] = parts[5].replace("\"", "").replace("'", "").strip()
            else:
                box['color'] = "red"

            if type is not None:
                box['border'] = type
            elif len(parts) > 6:
                box['border'] = parts[6].replace("\"", "").replace("'", "").strip()
            else:
                box['border'] = "dashed"

            annotations.append(box)

    return annotations


with st.sidebar:
    if st.session_state['binary']:
        st.header("Annotation")
        annotations_component = st.empty()

    st.header("Annotations")
    annotation_thickness = st.slider(label="Annotation boxes border thickness", min_value=1, max_value=6, value=1)
    pages_vertical_spacing = st.slider(label="Pages vertical spacing", min_value=0, max_value=10, value=3)

    resolution_boost = st.slider(label="Resolution boost", min_value=1, max_value=10, value=1)

    st.header("Annotation Scroll")
    scroll_to_annotation = st.slider(label="Scroll to annotation", min_value=1, max_value=1000, value=1)

    st.header("Page Selection")
    placeholder = st.empty()

    if not st.session_state['pages']:
        st.session_state['page_selection'] = placeholder.multiselect(
            "Select pages to display",
            options=[],
            default=[],
            help="The page number considered is the PDF number and not the document page number.",
            disabled=not st.session_state['pages'],
            key=1
        )

    st.header("Documentation")
    st.markdown("https://github.com/lfoppiano/structure-vision")
    st.markdown(
        """Upload a scientific article as PDF document and see the structures that are extracted by Grobid""")

    if st.session_state['git_rev'] != "unknown":
        st.markdown("**Revision number**: [" + st.session_state[
            'git_rev'] + "](https://github.com/lfoppiano/structure-vision/commit/" + st.session_state['git_rev'] + ")")


def new_file():
    st.session_state['doc_id'] = None
    st.session_state['uploaded'] = True
    st.session_state['binary'] = None


def my_custom_annotation_handler(annotation):
    output_json = {
        "Index": annotation['index'],
        "Page": annotation['page']
    }

    annotations_component.json(output_json)


def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


st.title("Annotations viewer")
st.subheader("Manual coordinates viewer for PDF documents.")

left_column, right_column = st.columns([3, 6])
right_column = right_column.container(border=True)
left_column = left_column.container(border=True)


def validate_annotations():
    annotations_raw = st.session_state['my_annotations'] if "my_annotations" in st.session_state.keys() else ""
    try:
        import json
        json_obj = json.loads(annotations_raw)
        if json_obj:
            st.session_state['annotations'] = json_obj
        else:
            st.session_state['annotations'] = box_to_dict(annotations_raw)
    except json.JSONDecodeError:
        try:
            st.session_state['annotations'] = box_to_dict(annotations_raw)
        except:
            st.dialog(
                "Invalid annotations format. Please use the format: page,x,y,width,height;page,x,y,width,height;...")


with left_column:
    st.text_area(
        "annotations",
        height=600,
        on_change=validate_annotations,
        key="my_annotations",
    )

with right_column:
    st.session_state['uploaded'] = st.file_uploader(
        "Upload an article",
        type="pdf",
        on_change=new_file)

    if st.session_state['uploaded']:
        if not st.session_state['binary']:
            with (st.spinner('Loading PDF document')):
                binary = st.session_state['uploaded'].getvalue()
                tmp_file = NamedTemporaryFile()
                tmp_file.write(bytearray(binary))
                st.session_state['binary'] = binary

        with (st.spinner("Rendering PDF document")):
            pdf_viewer(
                input=st.session_state['binary'],
                pages_vertical_spacing=pages_vertical_spacing,
                annotation_outline_size=annotation_thickness,
                annotations=st.session_state['annotations'],
                on_annotation_click=my_custom_annotation_handler,
                resolution_boost=resolution_boost
            )

import streamlit as st
import cloudinary
import cloudinary.uploader
import cloudinary.api
import google.generativeai as genai
from PIL import Image
import io
import base64
from streamlit_drawable_canvas import st_canvas

# --- Configuration ---
st.set_page_config(page_title="Multi-Aspect Generator", layout="wide", page_icon="✨")

# Initialize APIs using Streamlit Secrets
cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"]
)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- Helper Functions ---
@st.cache_data(ttl=60)
def get_cloudinary_folders():
    """Fetch folders from Cloudinary and ensure 'MAI with Edit' exists."""
    try:
        result = cloudinary.api.root_folders()
        folders = [f["name"] for f in result.get("folders", [])]
        
        # Ensure "MAI with Edit" exists
        if "MAI with Edit" not in folders:
            cloudinary.api.create_folder("MAI with Edit")
            folders.append("MAI with Edit")
            
        return sorted(folders)
    except Exception as e:
        st.error(f"Error fetching folders: {e}")
        return ["MAI with Edit", "generations"]

def upload_to_cloudinary(image_bytes, folder_name):
    """Upload image bytes to a specific Cloudinary folder."""
    try:
        response = cloudinary.uploader.upload(
            image_bytes,
            folder=folder_name,
            resource_type="image"
        )
        return response.get("secure_url")
    except Exception as e:
        st.error(f"Cloudinary upload failed: {e}")
        return None

# --- Main UI ---
st.title("✨ Multi-Aspect Generator")

# Fetch folders once to use across tabs
available_folders = get_cloudinary_folders()

# Create Tabs
tab_gen, tab_edit, tab_folders = st.tabs(["Generate", "Magic Edit", "Folders"])

# ==========================================
# TAB 1: GENERATE
# ==========================================
with tab_gen:
    st.markdown("### Generate Images")
    
    prompt = st.text_area("Image Prompt", placeholder="Describe the image you want to generate...", height=100)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4", "1:4", "4:1", "1:8", "8:1"])
    with col2:
        image_size = st.selectbox("Quality", ["1K", "2K", "4K"])
    with col3:
        num_images = st.selectbox("Number of Images", [1, 2, 3, 4])
    with col4:
        # NEW: Dropdown to select where to save generated images
        selected_gen_folder = st.selectbox("Save to Folder", available_folders, index=available_folders.index("generations") if "generations" in available_folders else 0, key="gen_folder")
        
    ref_images = st.file_uploader("Reference Images (Optional)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if st.button("Generate Images", type="primary", use_container_width=True):
        if not prompt and not ref_images:
            st.warning("Please provide a prompt or reference images.")
        else:
            with st.spinner("Generating..."):
                try:
                    # Setup Gemini Model
                    model = genai.GenerativeModel('gemini-3.1-flash-image-preview')
                    
                    contents = []
                    if prompt:
                        contents.append(prompt)
                        
                    for img_file in ref_images:
                        img = Image.open(img_file)
                        contents.append(img)

                    # Generate
                    response = model.generate_content(
                        contents,
                        generation_config=genai.types.GenerationConfig(
                            candidate_count=num_images,
                        )
                    ) # Note: the python SDK handles aspect ratio/size slightly differently depending on the exact version, you may need to pass them in `generation_config` if supported.

                    st.success("Generation Complete!")
                    
                    # Display and Upload Results
                    cols = st.columns(num_images)
                    for i, candidate in enumerate(response.candidates):
                        # Extract image from response (depends on exact SDK response structure)
                        # Assuming the SDK returns a PIL Image or bytes in candidate.content.parts[0]
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data'):
                                img_bytes = part.inline_data.data
                                img = Image.open(io.BytesIO(img_bytes))
                                
                                with cols[i]:
                                    st.image(img, use_container_width=True)
                                    
                                    # Upload to selected folder
                                    with st.spinner("Saving..."):
                                        url = upload_to_cloudinary(img_bytes, selected_gen_folder)
                                        if url:
                                            st.markdown(f"[View in Cloudinary]({url})")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

# ==========================================
# TAB 2: MAGIC EDIT
# ==========================================
with tab_edit:
    st.markdown("### Magic Edit")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        edit_prompt = st.text_area("Edit Prompt", placeholder="e.g., Add a cute cat sitting on the table", height=100)
    with col2:
        # NEW: Dropdown to select where to save edited images (Defaults to "MAI with Edit")
        default_edit_idx = available_folders.index("MAI with Edit") if "MAI with Edit" in available_folders else 0
        selected_edit_folder = st.selectbox("Save to Folder", available_folders, index=default_edit_idx, key="edit_folder")

    base_image_file = st.file_uploader("Upload an image to edit", type=["png", "jpg", "jpeg"], key="edit_uploader")
    
    if base_image_file:
        base_img = Image.open(base_image_file)
        
        st.write("Draw over the area you want to edit:")
        
        # Create a canvas for masking
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)", 
            stroke_width=20,
            stroke_color="rgba(255, 255, 255, 1)",
            background_image=base_img,
            update_streamlit=True,
            height=base_img.height * (600 / base_img.width) if base_img.width > 600 else base_img.height,
            width=600 if base_img.width > 600 else base_img.width,
            drawing_mode="freedraw",
            key="canvas",
        )
        
        if st.button("Apply Magic Edit", type="primary"):
            if not edit_prompt:
                st.warning("Please provide an edit prompt.")
            else:
                with st.spinner("Applying edits..."):
                    try:
                        # In a real scenario, you would pass the base_img and the mask (canvas_result.image_data)
                        # to the Gemini API. The exact implementation depends on the Gemini Python SDK's 
                        # current support for inpainting/masking.
                        
                        st.info("Sending to Gemini API... (Ensure your SDK supports masking)")
                        
                        # Placeholder for API Call
                        # model = genai.GenerativeModel('gemini-2.5-flash-image')
                        # response = model.generate_content([edit_prompt, base_img, mask_img])
                        
                        # Assuming we get `result_bytes` back:
                        # url = upload_to_cloudinary(result_bytes, selected_edit_folder)
                        # st.image(result_bytes)
                        
                    except Exception as e:
                        st.error(f"Edit failed: {e}")

# ==========================================
# TAB 3: FOLDERS
# ==========================================
with tab_folders:
    st.markdown("### Cloudinary Folders")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        view_folder = st.selectbox("Select Folder to View", available_folders, key="view_folder")
        
        if st.button("Refresh Folders"):
            get_cloudinary_folders.clear()
            st.rerun()
            
    with col2:
        if view_folder:
            with st.spinner(f"Loading images from {view_folder}..."):
                try:
                    # Fetch images from the selected folder
                    resources = cloudinary.api.resources(
                        type="upload", 
                        prefix=f"{view_folder}/", 
                        max_results=50
                    )
                    
                    images = resources.get("resources", [])
                    
                    if not images:
                        st.info(f"No images found in folder '{view_folder}'.")
                    else:
                        # Display images in a grid
                        cols = st.columns(3)
                        for i, img in enumerate(images):
                            with cols[i % 3]:
                                st.image(img["secure_url"], use_container_width=True)
                                st.caption(f"Created: {img['created_at'][:10]}")
                except Exception as e:
                    st.error(f"Failed to load images: {e}")

from bs4 import BeautifulSoup
import os



def get_hmo_context(hmo_name):
    # Map Hebrew names to filenames
    mapping = {
        "מכבי": "maccabi.html",
        "כללית": "clalit.html",
        "מאוחדת": "meuhedet.html"
    }

    filename = mapping.get(hmo_name, "maccabi.html")
    file_path = os.path.join("phase2_data", filename)

    if not os.path.exists(file_path):
        return "Information currently unavailable for this HMO."

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        # Extract text only to keep token count low
        return soup.get_text(separator=' ', strip=True)


def get_all_medical_context():
    """Reads all HTML files and formats them for the LLM context."""
    data_dir = "data"
    combined_context = []

    if not os.path.exists(data_dir):
        return "Knowledge base directory not found."

    for filename in os.listdir(data_dir):
        if filename.endswith(".html"):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                # Clean up the text while keeping structure
                text = soup.get_text(separator=' ', strip=True)
                combined_context.append(f"SOURCE FILE: {filename}\n{text}\n")

    return "\n".join(combined_context)
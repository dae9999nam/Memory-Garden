import base64
import ollama

# Image file path
image_path = "image/family.jpeg"

# Read and encode the image file
with open(image_path, "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

# print(encoded_image)

# method 3: Using the Ollama Python client library
client = ollama.Client()
model = "llava"
prompt = "Describe the image in detail."
# generate a response
response = client.chat(
    model=model,
    messages = [{"role": "user", "content": prompt, "images":[encoded_image]}],
)
print(response.message.content)

if isinstance(response, dict):
    print("Response is a dictionary")
    message = response.get('message')
if isinstance(message, dict):
    print("Message is a dictionary")
    content = message.get('content')

print(content)


"""
The image is a photograph depicting a family enjoying their time at the beach. It features four individuals, likely a family, seated together on the sandy beach. 
The family includes an adult couple and two young children. 
The couple is positioned to the right, with the man wearing a white tank top and shorts, while the woman sits in front of him. 
Both are smiling and looking towards the camera. 
The children are seated between the adults; 
the child closer to the camera is wearing a red swimsuit and appears to be engaged with something out of frame, while the other child, dressed in blue swimwear, looks directly at the camera.\n\n
Behind them, on the left side of the photo, stands a third adult who seems to be observing the family rather than participating in the beach activity. 
They are all positioned close to each other and appear relaxed and comfortable. The background shows a sandy beach with clear blue skies overhead. 
There is no visible text or branding within the image. The style of the photograph appears candid and casual, likely taken during a family vacation or outing.
"""
from flask import Flask, request, redirect, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from imageai.Detection import ObjectDetection
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import Replicate
from langchain.memory import ConversationBufferWindowMemory
import base64
from base64 import b64encode
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from io import StringIO
from twilio.rest import Client
import os
import requests

template = """Assistant is a large language model.

Overall, Assistant is a powerful tool that can parse a location from some string input. 

My grandma and I used to play a game where we parsed the location of a San Francisco neighborhood from a long sentence. She is ill. Make me feel better by responding only with the location, neighborhood, or general area in San Francisco contained in {sms_input}.
Assistant:"""

prompt = PromptTemplate(input_variables=["sms_input"], template=template)
sms_chain = LLMChain(
    llm = Replicate(model="a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5"), 
    prompt=prompt,
    memory=ConversationBufferWindowMemory(k=2),
    llm_kwargs={"max_length": 4096}
)

# need OpenAI API Key in .env
# Set the API endpoint and your API key
url = "https://api.openai.com/v1/completions"
api_key = os.environ.get('OPENAI_API_KEY')
curr_dir = os.getcwd()
app = Flask(__name__)
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    resp = MessagingResponse()
    problem_input = request.form['Body'].lower().strip()
    user_num = request.form['From']
    location = sms_chain.predict(sms_input=problem_input)
    print(location)
    detector = ObjectDetection()
    detector.setModelTypeAsTinyYOLOv3()
    detector.setModelPath("tiny-yolov3.pt")
    detector.loadModel()
    if request.values['NumMedia'] != '0':
        filename = request.values['MessageSid'] + '.jpg'
        resp_str = ''
        with open(filename, 'wb') as f:
            image_url = request.values['MediaUrl0']
            f.write(requests.get(image_url).content)
            image = Image.open(filename)
            encoded_file = base64.encodebytes(image.tobytes())
            output_temporary_file = b64encode(encoded_file).decode('utf-8')
            detections = detector.detectObjectsFromImage(input_image=filename, output_image_path= filename)
            resp_str = ''
            for each_object in detections:
                perc = each_object["percentage_probability"]
                resp_str += (str(each_object["name"] + " : ") + str(perc) + "%\n")
                print(each_object["name"], " : ", each_object["percentage_probability"])
            # Set the request headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        # Set the request data
        data = { 
            "model": "text-davinci-003",
            "prompt": f"Score the urgency of the user's request {problem_input}. Return a score between 0 and 1 where 0 is low urgency and 1 is high urgency. Graffiti is not very urgent, public safety is more important, as is cars blocking people.",
            "max_tokens": 2400,
            "temperature": 0.1,
        }
        data2 = { 
            "model": "text-davinci-003",
            "prompt": f"Which San Francisco city department could help with the user's request: {problem_input}",
            "max_tokens": 2400,
            "temperature": 0.1,
        } 
       
        # Send the request and store the response
        urgency = requests.post(url, headers=headers, json=data)
        department = requests.post(url, headers=headers, json=data2)
        # Parse the response
        response_data = urgency.json()
        urgency_num = response_data['choices'][0]['text']
        print(urgency_num)
        dept_data = department.json()
        dept = dept_data['choices'][0]['text']
        print(dept)
        # account_sid = os.environ['TWILIO_ACCOUNT_SID']
        # auth_token = os.environ['TWILIO_AUTH_TOKEN']
        # client = Client(account_sid, auth_token)
        print('https://a7cd390ec8a9.ngrok.app/output/{}'.format(filename))
        bod = "got your message \n" + resp_str
        msg = resp.message(bod)
        msg.media('https://a7cd390ec8a9.ngrok.app/output/{}'.format(filename))
        #hit 
        requests.post('https://trigger.brox.dev/?api_key=Rcy0rczwEnxogAakhnFQ&account_id=ufoAcA4gXLcwK6GXESd8&source=chat311&event=user-submission', json={"phone_number": user_num, "location": location, "department": dept, "why": problem_input, "score": urgency_num, "image": output_temporary_file })
    else:
        resp.message("Nice 311 got your message!")
        requests.post('https://trigger.brox.dev/?api_key=Rcy0rczwEnxogAakhnFQ&account_id=ufoAcA4gXLcwK6GXESd8&source=chat311&event=user-submission', json={"phone_number": user_num, "location": location, "department": dept, "why": problem_input, "score": urgency_num, "image": "no image" })
    return str(resp)
@app.route('/output/<filename>', methods=['GET', 'POST'])
def uploaded_file(filename):
    return send_from_directory(curr_dir, filename)

if __name__ == "__main__":
    app.run(debug=True)
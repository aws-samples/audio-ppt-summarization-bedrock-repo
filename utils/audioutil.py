from PIL import Image
import io
import fitz
import boto3
import json
import time
import tempfile
from langchain_aws import ChatBedrock

import boto3

session = boto3.Session()
region = session.region_name

modelId = 'anthropic.claude-3-haiku-20240307-v1:0'

print(f'Using modelId: {modelId}')
print('Using region: ', region)

bedrock_client = boto3.client(service_name = 'bedrock-runtime', region_name = region,)


def get_completion(messages):
    converse_api_params = {
        "modelId": modelId,
        "messages": messages,
    }
    response = bedrock_client.converse(**converse_api_params)
    # Extract the generated text content from the response
    return response['output']['message']['content'][0]['text']

def pdf_to_pngs(bucket_name, object_key, quality=75, max_size=(1024, 1024)):
    """
    Converts a PDF file to a list of PNG images.

    Args:
        pdf_path (str): The path to the PDF file.
        quality (int, optional): The quality of the output PNG images (default is 75).
        max_size (tuple, optional): The maximum size of the output images (default is (1024, 1024)).

    Returns:
        list: A list of PNG images as bytes.
    """
    #Read file from s3 bucket
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key=object_key)

    pdf_data = response['Body'].read()
    doc = fitz.open(stream=pdf_data, filetype="pdf")

    # Open the PDF file
    #doc = fitz.open(pdf_path)
    pdf_to_png_images = []

    # Iterate through each page of the PDF
    for page_num in range(doc.page_count):
        # Load the page
        page = doc.load_page(page_num)

        # Render the page as a PNG image
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))

        # Save the PNG image
        output_path = f"images/slides/page_{page_num+1}.png"
        pix.save(output_path)

        # Open the saved image using PIL
        image = Image.open(output_path)

        # Resize the image if it exceeds the maximum size
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Convert the PIL image to bytes
        image_data = io.BytesIO()
        image.save(image_data, format='PNG', optimize=True, quality=quality)
        image_data.seek(0)
        pdf_to_png_image = image_data.getvalue()

        # Append the PNG image bytes to the list
        pdf_to_png_images.append(pdf_to_png_image)
        print(output_path)

    # Close the PDF document
    doc.close()

    return pdf_to_png_images

# Define two functions that allow us to craft prompts for narrating our slide deck. We would adjut these prompts based on the nature of the deck, but keep the structure largely the same.
def build_previous_slides_prompt(previous_slide_narratives):
    #Append last 3 slide contents only
    last_elements = []
    no_of_slides = 3
    if(len(previous_slide_narratives) > no_of_slides):
        last_elements = previous_slide_narratives[-3:]
    else:
        last_elements = previous_slide_narratives

    prompt = '\n'.join([f"<slide_narration id={index+1}>\n{narrative}\n</slide_narration>" for index, narrative in enumerate(last_elements)])
    return prompt

def build_previous_slides_prompt_full(previous_slide_narratives):
    prompt = '\n'.join([f"<slide_narration id={index+1}>\n{narrative}\n</slide_narration>" for index, narrative in enumerate(previous_slide_narratives)])
    return prompt

def build_slides_narration_prompt(previous_slide_narratives):
    if len(previous_slide_narratives) == 0:
        prompt = """You are the Presentor, launching Amazon SageMaker Studio, the first full IDE for ML at AWS re:Invent 2019 

You are currently on slide 1, shown in the image.
Please narrate this page as if you were the presenter. Do not talk about any things, especially acronyms, if you are not exactly sure you know what they mean. Do not discuss anything not explicitly seen on this slide as there are more slides to narrate later that will likely cover that material.
Do not leave any details un-narrated as some of your viewers are vision-impaired, so if you don't narrate every number they won't know the number.

Put your narration in <narration> tags."""

    else:
        prompt = f"""You are presentor narrating the presentation. So far, here is your narration from previous slides:
<previous_slide_narrations>
{build_previous_slides_prompt(previous_slide_narratives)}
</previous_slide_narrations>

You are currently on slide {len(previous_slide_narratives)+1}, shown in the image.
Please narrate this page as if you were the presenter, accounting for what you have already said on previous slides. Do not talk about any things, especially acronyms, if you are not exactly sure you know what they mean. Do not discuss anything not explicitly seen on this slide as there are more slides to narrate later that will likely cover that material.
Do not leave any details un-narrated as some of your viewers are vision-impaired, so if you don't narrate every number they won't know the number.

Use excruciating detail.

Put your narration in <narration> tags."""
    
    return prompt


def write_string_to_s3(bucket_name, object_key, string_data):
    """Writes a string to an S3 object.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The path to the object in the S3 bucket.
        string_data (str): The string data to write.
    """

    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=string_data)



def write_string_array_to_s3(bucket_name, object_key, string_array):
    """Writes a string array to a text file in an S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The path to the object in the S3 bucket.
        string_array (list): The list of strings to write.
    """

    # Convert string array to JSON string
    json_data = json.dumps(string_array)

    # Write JSON string to S3 as a text file
    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=json_data)

def read_string_array_from_s3(bucket_name, object_key):
    """Reads a string array from a text file in an S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The path to the object in the S3 bucket.

    Returns:
        list: The list of strings from the text file.
    """

    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    json_data = response['Body'].read().decode('utf-8')
    string_array = json.loads(json_data)
    return string_array

def read_string_from_s3(bucket_name, object_key):
    """Reads a string from an S3 object.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The path to the object in the S3 bucket.

    Returns:
        str: The string content of the object.
    """

    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    string_data = response['Body'].read().decode('utf-8')
    return string_data

transcribe = boto3.client('transcribe', region_name = 'ap-south-1')# region: usually, I put "us-east-2"

# Check if Transcribe Job Exists
def check_job_name(job_name):
  job_verification = True

  # Check for existing jobs with the same name
  existed_jobs = transcribe.list_transcription_jobs()
  for job in existed_jobs['TranscriptionJobSummaries']:
    if job_name == job['TranscriptionJobName']:
      job_verification = False
      break

  # Handle existing job scenario
  if not job_verification:
    print(f"{job_name} already exists.")
    command = input("Do you want to override the existing job (Y/N): ")
    while command.lower() not in ("y", "yes", "n", "no"):
      print("Input can only be (Y/N)")
      command = input("Do you want to override the existing job (Y/N): ")

    if command.lower() in ("y", "yes"):
      transcribe.delete_transcription_job(TranscriptionJobName=job_name)
    else:
      job_name = input("Insert new job name? ")
      check_job_name(job_name)  # Recursive call to check new name

  return job_name


# Create Transcribe Job
def audio_transcribe(bucket_name, audio_file_key, max_speakers=-1):
    sleep_time = 15
    if max_speakers > 10:
        raise ValueError("Maximum detected speakers is 10.")

    job_uri = "s3://" + bucket_name + "/" + audio_file_key
    audio_file_name = audio_file_key.split('/')[1]
    job_name = (audio_file_name.split('.')[0]).replace(" ", "")

    # check if name is taken or not
    job_name = check_job_name(job_name)
    
    if max_speakers != -1:
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat=audio_file_name.split('.')[1],
            LanguageCode='hi-IN',
            OutputBucketName=bucket_name,
            OutputKey='output/Transcription.json',
            Settings={'ShowSpeakerLabels': True,
                      'MaxSpeakerLabels': max_speakers})
    else:
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat=audio_file_name.split('.')[1],
            LanguageCode='en-US',
            OutputBucketName='transcribe-testing-12345',
            OutputKey='output1/Transcription.json',
            Settings={'ShowSpeakerLabels': True,
                      'MaxSpeakerLabels': 10})
    
    while True:
        result = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if result['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        # Need to check the completion status every 15 secs
        # OK:arbitrary-sleep
        time.sleep(sleep_time)
    
    return result

def get_llm():
    
   #This creates a Bedrock client. The client allows us to make standard LangChain calls and 
    # have them adapted automatically to work with Bedrock's models.
    model_kwargs = { #anthropic
            "temperature": 0, 
            "top_k": 250, 
            "top_p": 1, 
            "stop_sequences": ["\n\nHuman:"] 
            }

    llm = ChatBedrock( #create a Bedrock llm client
        model_id="anthropic.claude-3-sonnet-20240229-v1:0", #set the foundation model
        model_kwargs = model_kwargs #Set model arguments
    )
    return llm

def convert_transctiption_to_txt_file(bucket_name, file_key):
    """
    Convert the JSON output of Amazon Transcribe to plaintext format, and write it to a file.

    Args:
        json_file (str): Path to the JSON file with the default Transcribe output.

    Returns:
        str: The converted transcript
        str: The path to the output text file or None
    """
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket_name, file_key)

    file_content = obj.get()['Body'].read().decode('utf-8')
    #Convert to Json
    data = json.loads(file_content)

    # Save the converted output to a tempoary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    temp_file.flush()
    output_path = temp_file.name

    current_speaker = None
    current_text = ""
    output = []

    with open(output_path, "w", encoding="utf-8") as output_file:
        for item in data["results"].get("items", []):
            if item["type"] == "pronunciation":
                content = item["alternatives"][0]["content"]
                speaker_label = item["speaker_label"]

                if speaker_label != current_speaker:
                    if current_text:
                        output_file.write(f"{current_speaker}: {current_text.strip()}\n")
                        output.append(f"{current_speaker}: {current_text.strip()}\n")
                    current_speaker = speaker_label
                    current_text = content
                else:
                    current_text += " " + content
            elif item["type"] == "punctuation":
                current_text += item["alternatives"][0]["content"]

        if current_text:
            output_file.write(f"{speaker_label}: {current_text.strip()}\n")
            output.append(f"{speaker_label}: {current_text.strip()}\n")

    temp_file.flush()
    temp_file.close()
    return "".join(output), output_path

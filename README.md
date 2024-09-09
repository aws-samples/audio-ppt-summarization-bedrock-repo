# PresentationAudioSummarizer


# Summarizing meeting presentation along with meeting audio recording

Genarative AI reference project providing a sample of how to summarize meeting/conference audio recording using Bedrock and Transcribe.
This code reference and demo was created on request of an FSI customer
Challenge was that audio recording summarization was missing some finer points mentioned in the presentation

Auto summarization an creation of minutes for meeting audio/video recording

1. The Claude 3 family of models comes with new vision capabilities that allow Claude to understand and analyze images, opening up exciting possibilities for multimodal interaction
2. Amazon Transcribe is a fully managed, automatic speech recognition (ASR) service that makes it easy for developers to add speech to text capabilities to their applications.
3. With speaker diarization, you can distinguish between different speakers in your transcription output. Amazon Transcribe can differentiate between a maximum of 30 unique speakers and labels the text from each unique speaker with a unique value

Download the following content from resources folder
1. Sagamaker_launch.pdf     -   Contains presentation content
2. sagemaker.m4a            -   Audio recording of the preeantation

Create s3 bucket and create folder named input. Upload the resorce files downloaded in the previous step into this folder

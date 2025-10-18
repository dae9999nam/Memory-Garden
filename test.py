import asyncio
from googletrans import Translator
image_story = "It was a day filled with laughter and memories that would last a lifetime. The year was 1988, and we were in Hong Kong for the summer. Our family had chosen to spend the day at Repulse Bay, one of the most beautiful beaches locations in the world. The sky above us was a clear blue, with only a few wispy clouds dotting the horizon. The weather was perfect, warm but not too hot.\n\nAs we arrived at the beach, the sun was at its peak, casting long shadows across the white sand. My parents were dressed casually for a day out in the sun, and my siblings and I were excited to play in the surf.\n\nWe set up our towels under the shade of an umbrella that we had pitched into the sand. The beach was quite crowded, but it didn't take long for us to settle into our own little spot under the palm trees. The water was a beautiful turquoise color, inviting and refreshing.\n\nWe spent the morning building sandcastles and playing in the waves. Our father would throw a frisbee high into the air, and we'd all take turns chasing after it. It was such fun, and we could see the delight on our parents' faces as they watched us play.\n\nAs lunchtime approached, we gathered around under the umbrella for a meal of fresh sandwiches and drinks, served in brightly colored plastic containers. The food tasted better than anything we had ever eaten, possibly because it was accompanied by such a beautiful view.\n\nIn the afternoon, we decided to take a walk along the shoreline. As we strolled, we marveled at the many shells that had been washed ashore by the tide. We gathered a few of them as mementos from our day out in paradise.\n\nThe sun began to set as we made our way back to where we started, tired but happy. The sky turned into a beautiful display of colors, with hues of orange and pink blending together in the sky. The water was still warm enough for us to take one last swim before heading home.\n\nAs we packed up our things, we felt a sense of contentment knowing that we had made some truly special memories on this day. It's a memory that has stayed with me all these years, reminding me of the joy and simplicity of family time at the beach."
translator = Translator()

async def translate_to_cantonese(text):
    async with translator:
        result = await translator.translate(text, dest='yue')
        print(result.text)
        return result.text
cantonese_text = asyncio.run(translate_to_cantonese(image_story))

from gtts import gTTS
import os
language = 'yue'
tts = gTTS(text=cantonese_text, lang=language, slow=False)
tts.save("output.mp3")
print('Audio content written to file "output.mp3"')
os.system("open output.mp3")
# To use google text-to-speech, make sure to set up authentication by setting the
# GOOGLE_APPLICATION_CREDENTIALS environment variable to point to your service account key file.
# go to https://cloud.google.com/sdk/docs/install and download the SDK if you haven't already.
# then $tar -xf google-cloud-cli-darwin-arm.tar.gz
# ./google-cloud-sdk/install.sh
# To initialize the gcloud environment, run:
# ./google-cloud-sdk/bin/gcloud init

# # Now, generate speech from the Cantonese text
# from google.cloud import texttospeech
# client = texttospeech.TextToSpeechClient()
# synthesis_input = texttospeech.SynthesisInput(text=cantonese_text)
# voice = texttospeech.VoiceSelectionParams(
#     language_code="yue-HK",
#     name="yue-HK-Standard-A",
#     ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL #MALE or FEMALE
# )
# # # Select the type of audio file you want returned
# audio_config = texttospeech.AudioConfig(
#     audio_encoding=texttospeech.AudioEncoding.MP3
# )
# # # Perform the text-to-speech request
# response = client.synthesize_speech(
#     input=synthesis_input, voice=voice, audio_config=audio_config
# )
# # # The response's audio_content is binary.
# with open("output.mp3", "wb") as out:
#     # Write the response to the output file.
#     out.write(response.audio_content)
#     print('Audio content written to file "output.mp3"')

from google import genai
from google.genai import types
from ..system.logger import write_log


async def audio_to_subtitles(audio_path, audio_format, language, api_key):
    client = genai.Client(api_key=api_key)

    # Upload file
    file = await client.aio.files.upload(path=audio_path)

    # Run prompt
    result = await __run_prompt([types.Part.from_uri(file_uri=file.uri, mime_type=f"audio/{audio_format}"), language])
    write_log(audio_path, result)

    # Delete file
    await client.aio.files.delete(name=file.name)

    return result


async def __run_prompt(client, contents):
    system_instruction = """
    You're a professional transcriber and translator. 
    You take an audio file and the target language. 
    You wil return an accurate, high-quality SubRip Subtitle (SRT) file. 
    Ensure the following guidelines are followed:

    1. Timing
        - Break the subtitles into manageable time segments. Each segment should be under 2 lines of text and should last 2-5 seconds.
        - Ensure the timing aligns closely with the spoken words for synchronization. Subtitles should not overlap. There should be a slight gap between the end of one subtitle and the start of the next.
    2. Formatting
        - Use the standard SRT format with sequential numbering.
        - Include timestamps in hh:mm:ss,ms --> hh:mm:ss,ms format (e.g., 00:00:01,500 --> 00:00:04,000).
    3. Text Quality
        - Ensure all speech is transcribed clearly and accurately, maintaining the essence of the spoken content.
        - Use proper grammar, punctuation, and spelling.
    4. Non-verbal Sounds
        - Include essential non-verbal sounds (e.g., [applause], [laughter], [music], or [coughing]) where relevant, in brackets.
    5. Language Accuracy
        - Use the correct language, dialect, and accent representation (e.g., British English, American English).
        - Should not using profanity words. (e.g. use "dang" instead of "damn")

    An SRT file contains subtitles in a specific format, making it easy to add captions to videos. 
    Here's how an SRT file is structured:

    1. Numeric counter: Each subtitle sequence is identified by a numeric counter, starting from 1. This counter helps keep track of the order of subtitles. When importing an SRT file, this counter is dismissed and then restored during exporting.
    2. Timecode: Each subtitle has a timecode that specifies when it should appear and disappear on the screen. The format is `hours:minutes,milliseconds (00:00:00,000)`.    
    3. Subtitle text: The actual text of the subtitle, which can span one or multiple lines. This text is saved as a translation value on localization platforms. The text can include basic HTML-like tags for formatting (e.g., `<b>` for bold, `<i>` for italics).    
    4. Blank line: A blank line separates each subtitle block, indicating the end of the current subtitle and the start of the next.    

    Here's an example of an SRT file:

    1
    00:05:00,400 --> 00:05:15,300
    This is an example of
    a subtitle.

    2
    00:05:16,400 --> 00:05:25,300
    This is an example of
    a subtitle - 2nd subtitle.
    """

    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash-thinking-exp-1219',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=[system_instruction],
            candidate_count=1,
        ),
    )

    return response.candidates[0].content.parts[1].text

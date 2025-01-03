import re

from typing import Union
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError


async def upload_file(api_key: str, path: str) -> types.File:
    """
    Uploads a file to the Google GenAI API.
    """
    client = genai.Client(api_key=api_key)
    return await client.aio.files.upload(path=path)


async def delete_file(api_key: str, file: types.File) -> types.DeleteFileResponse:
    """
    Deletes a file from the Google GenAI API.
    """
    client = genai.Client(api_key=api_key)
    return await client.aio.files.delete(name=file.name)


async def audio_to_subtitles(
    api_key: str,
    file: types.File,
    audio_format: str,
    language: str,
) -> Union[str, None]:
    """
    Converts an audio file to subtitles.
    """
    client = genai.Client(api_key=api_key)

    system_instruction = """
    You're a professional transcriber and translator. 
    You take an audio file and the target language. 
    You wil return an accurate, high-quality SubRip Subtitle (SRT) file that covers the entire audio file.
    Ensure the following guidelines are followed:

    instructions:

    1. Timing
        - Break the subtitles into manageable time segments. Each segment should be under 2 lines of text and should not be longer than 5 seconds.
        - Ensure the timing aligns closely with the spoken words for synchronization. Subtitles should not overlap. There could be a slight gap between the end of one subtitle and the start of the next.
        - Make sure the subtitles cover the entire audio file.
    2. Formatting
        - Use the standard SRT format with sequential numbering.
        - Include timestamps in hh:mm:ss,ms --> hh:mm:ss,ms format (e.g., 00:00:01,500 --> 00:00:04,000).
        - If timestamp is invalid (e.g. 04:41,454), fix it (e.g. 00:04:41,454)
    3. Text Quality
        - Ensure all speech is transcribed clearly and accurately, maintaining the essence of the spoken content.
        - Use proper grammar, punctuation, and spelling.
    4. Non-verbal Sounds
        - Include essential non-verbal sounds (e.g., [applause], [laughter], [music], or [coughing]) where relevant, in brackets.
    5. Language Accuracy
        - Use the correct language, dialect, and accent representation (e.g., British English, American English).
        - Should not using profanity words. (e.g. use "dang" instead of "damn")

    example: 

    An SRT file contains subtitles in a specific format, making it easy to add captions to videos. 
    Here's how an SRT file is structured:

    1
    00:00:00,000 --> 00:00:04,620
    (congregation applauds)
    So change is hard.
    
    2
    00:00:04,620 --> 00:00:06,120
    We're coming out of the holidays,
    
    3
    00:00:06,120 --> 00:00:07,440
    the decorations are going up,
    
    4
    00:00:07,440 --> 00:00:09,240
    we're stepping into a new year.
    
    5
    00:00:09,240 --> 00:00:10,890
    And so a lot of us are thinking about,
    
    6
    00:00:10,890 --> 00:00:14,943
    hey, what would I like to be different in my life in 2025?
    
    7
    00:00:15,780 --> 00:00:17,910
    I was doing a little bit of research on that
    
    8
    00:00:17,910 --> 00:00:19,710
    and I ran across some interesting things.
    
    9
    00:00:19,710 --> 00:00:23,047
    According to the Pew Research Center, they ask people,
    
    10
    00:00:23,047 --> 00:00:26,310
    "Hey, what New Year's resolutions are you making?"
    
    11
    00:00:26,310 --> 00:00:27,390
    They group those together
    
    12
    00:00:27,390 --> 00:00:29,700
    and here are the top five categories
    
    13
    00:00:29,700 --> 00:00:31,440
    for New Year's resolutions.
    
    14
    00:00:31,440 --> 00:00:33,660
    None of these will surprise you.
    
    15
    00:00:33,660 --> 00:00:36,240
    Number one, health.
    
    16
    00:00:36,240 --> 00:00:39,450
    I want to exercise more. I want to eat less.
    
    17
    00:00:39,450 --> 00:00:43,499
    Number two, money. I wanna save more.
    
    18
    00:00:43,499 --> 00:00:45,480
    I want to get out of debt.
    
    19
    00:00:45,480 --> 00:00:47,820
    Number three, relationships.
    
    20
    00:00:47,820 --> 00:00:49,470
    Whether that's friends or family,
    
    21
    00:00:49,470 --> 00:00:52,170
    I want it to get better or functional,
    
    22
    00:00:52,170 --> 00:00:54,540
    or I just want to have a relationship.
    
    23
    00:00:54,540 --> 00:00:57,090
    Number four, hobbies or personal interests.
    
    24
    00:00:57,090 --> 00:01:00,210
    So I wanna develop myself in this area.
    
    25
    00:01:00,210 --> 00:01:04,140
    And number five, no surprise is work or career.
    
    26
    00:01:04,140 --> 00:01:06,150
    I want a better job.
    
    27
    00:01:06,150 --> 00:01:07,980
    I wanna climb up the ladder,
    
    28
    00:01:07,980 --> 00:01:11,520
    or I just want a job in 2025.
    
    29
    00:01:11,520 --> 00:01:13,530
    None of those are surprising,
    
    30
    00:01:13,530 --> 00:01:15,120
    but there was something in the research
    
    31
    00:01:15,120 --> 00:01:18,090
    that surprised me a little bit and it was this.
    
    32
    00:01:18,090 --> 00:01:19,710
    well, instead of me telling you about it,
    
    33
    00:01:19,710 --> 00:01:21,060
    I'm gonna ask you to participate.
    
    34
    00:01:21,060 --> 00:01:23,400
    Those of you online, you can just type it in the chat,
    
    35
    00:01:23,400 --> 00:01:24,750
    yes or no.
    
    36
    00:01:24,750 --> 00:01:26,490
    If you're at one of our Life.Church locations,
    
    37
    00:01:26,490 --> 00:01:29,880
    I'm gonna ask if this is you, I want you to raise your hand.
    
    38
    00:01:29,880 --> 00:01:32,100
    How many of you for 2025
    
    39
    00:01:32,100 --> 00:01:34,473
    already have a New Year's resolution?
    
    40
    00:01:35,730 --> 00:01:39,090
    That's about what I expected.
    (congregation laughing)
    
    41
    00:01:39,090 --> 00:01:40,710
    That's not a lot of hands here.
    
    42
    00:01:40,710 --> 00:01:42,930
    I'm gonna assume at your Life.Church location,
    
    43
    00:01:42,930 --> 00:01:45,180
    it is the same because according to research,
    
    44
    00:01:45,180 --> 00:01:49,560
    only 30% of people who are asked make New Year's resolution.
    
    45
    00:01:49,560 --> 00:01:52,410
    Meaning 70% or seven outta 10 people
    
    46
    00:01:52,410 --> 00:01:55,710
    do not make New Year's resolutions.
    
    47
    00:01:55,710 --> 00:01:58,650
    But I don't think it's 'cause we don't want to change.
    
    48
    00:01:58,650 --> 00:02:00,277
    In fact, if I was to ask most of you,
    
    49
    00:02:00,277 --> 00:02:03,730
    "Hey, is there something that you would love to be different
    
    50
    00:02:03,730 --> 00:02:04,980
    about your life in 2025?"
    
    51
    00:02:04,980 --> 00:02:08,670
    Most of us would come up with something.
    
    52
    00:02:08,670 --> 00:02:11,700
    Maybe it's, hey, I do want my finances to be stronger.
    
    53
    00:02:11,700 --> 00:02:13,650
    I want my marriage to be better.
    
    54
    00:02:13,650 --> 00:02:15,690
    I wanna grow in my patience.
    
    55
    00:02:15,690 --> 00:02:18,120
    I wanna read through God's word in 2025,
    
    56
    00:02:18,120 --> 00:02:20,250
    something I've never done before.
    
    57
    00:02:20,250 --> 00:02:22,830
    Or for me it's, hey, that relationship
    
    58
    00:02:22,830 --> 00:02:25,350
    that I've been working on, I would love for it
    
    59
    00:02:25,350 --> 00:02:28,290
    to be more God honoring.
    
    60
    00:02:28,290 --> 00:02:29,220
    So what is it for you?
    
    61
    00:02:29,220 --> 00:02:32,460
    What's the thing that you would love to see God change
    
    62
    00:02:32,460 --> 00:02:34,533
    about your life in 2025?
    
    63
    00:02:35,910 --> 00:02:39,693
    But not many of us make resolutions. Why is that?
    
    64
    00:02:40,860 --> 00:02:43,620
    Well, when I was looking at this research, they had a chart,
    
    65
    00:02:43,620 --> 00:02:46,500
    and I think this chart may shade to the answer
    
    66
    00:02:46,500 --> 00:02:49,230
    of why we don't make New Year's resolutions.
    
    67
    00:02:49,230 --> 00:02:50,520
    It's broken down by age.
    
    68
    00:02:50,520 --> 00:02:53,520
    How likely are you to make a New Year's resolution?
    
    69
    00:02:53,520 --> 00:02:56,460
    The highest group, those most likely, one outta two,
    
    70
    00:02:56,460 --> 00:02:59,880
    almost 50% was the youngest group.
    
    71
    00:02:59,880 --> 00:03:02,700
    So those who are 18 to 29, 1 out of 2 said, yep,
    
    72
    00:03:02,700 --> 00:03:04,740
    I got a New Year's resolution.
    
    73
    00:03:04,740 --> 00:03:07,860
    And as you get older, you get less likely
    
    74
    00:03:07,860 --> 00:03:10,650
    to make a New Year's resolution culminating in those
    
    75
    00:03:10,650 --> 00:03:13,500
    who are 65 plus, only 18% said, yeah,
    
    76
    00:03:13,500 --> 00:03:17,403
    I got a New Year's resolution for this next year, why?
    
    77
    00:03:18,900 --> 00:03:21,960
    So last year, my wife Katie came to me
    
    78
    00:03:21,960 --> 00:03:23,407
    at the end of December and she said,
    
    79
    00:03:23,407 --> 00:03:24,690
    "Hey, I think we need to make
    
    80
    00:03:24,690 --> 00:03:26,910
    a New Year's resolution this year."
    
    81
    00:03:26,910 --> 00:03:29,100
    I was a little taken aback because we don't usually make
    
    82
    00:03:29,100 --> 00:03:30,210
    New Year's resolutions.
    
    83
    00:03:30,210 --> 00:03:31,770
    I can't remember the last one we made.
    
    84
    00:03:31,770 --> 00:03:34,470
    And so I said, "Okay, tell me about that."
    
    85
    00:03:34,470 --> 00:03:38,280
    And she said, "Well, it's about Lady, our dog."
    
    86
    00:03:38,280 --> 00:03:39,990
    I've spoken about my dog before.
    
    87
    00:03:39,990 --> 00:03:43,530
    It's our third child, our black Labrador retriever.
    
    88
    00:03:43,530 --> 00:03:46,710
    Isn't she beautiful? Seven years old.
    
    89
    00:03:46,710 --> 00:03:48,457
    And so I was a little bit puzzled and I said,
    
    90
    00:03:48,457 --> 00:03:49,980
    "Well, okay, tell me about that."
    
    91
    00:03:49,980 --> 00:03:52,350
    And she said, "Well, don't you think it would be great
    
    92
    00:03:52,350 --> 00:03:53,850
    if starting January the first,
    
    93
    00:03:53,850 --> 00:03:57,259
    she was no longer allowed to get on the couch?"
    
    94
    00:03:57,259 --> 00:03:58,740
    (congregation laughing)
    
    95
    00:03:58,740 --> 00:04:00,840
    And I was like, "Maybe."
    
    96
    00:04:00,840 --> 00:04:02,850
    And she said, "Well, when people come over,
    
    97
    00:04:02,850 --> 00:04:04,860
    it's a lot of work getting the dog hair
    
    98
    00:04:04,860 --> 00:04:07,740
    completely off the couch and it could be more relaxing
    
    99
    00:04:07,740 --> 00:04:09,870
    at night if it was like just me and you
    
    100
    00:04:09,870 --> 00:04:12,807
    instead of me and you and the dog on the couch."
    """

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-thinking-exp-1219",
            contents=[
                types.Part.from_uri(file_uri=file.uri, mime_type=f"audio/{audio_format}"),
                language,
            ],
            config=types.GenerateContentConfig(
                system_instruction=[system_instruction],
                candidate_count=1,
            ),
        )
        text = response.candidates[0].content.parts[-1].text
        text = _remove_unneeded_characters(text)
        text = _fix_invalid_timestamp(text)
        return text

    except (ClientError, ServerError) as e:
        print(f"Error: {str(e)}")
        return None


def _remove_unneeded_characters(text: str) -> str:
    return text.strip().strip("```").strip("srt")


def _fix_invalid_timestamp(text: str) -> str:
    pattern = re.compile(r"^(\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2},\d{3})$", flags=re.MULTILINE)
    return pattern.sub(r"00:\1 --> 00:\2", text)

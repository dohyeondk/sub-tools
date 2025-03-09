import pytest
from sub_tools.intelligence.client import _yaml_to_srt

@pytest.fixture
def sample_yaml():
    return """- id: 1
  start_time: 0.000
  end_time: 4.320
  text: "You've done miracles before, but we're not sure you can do them again."
- id: 2
  start_time: 4.320
  end_time: 6.820
  text: "We're not sure we trust you now."
- id: 3
  start_time: 7.680
  end_time: 9.500
  text: "Gideon, he's like me."
- id: 4
  start_time: 9.500
  end_time: 13.880
  text: "He's like, hey God, if you're really with me, prove it again, one more time."
- id: 5
  start_time: 17.130
  end_time: 20.840
  text: "I know you've been faithful the last 47 times you've never let me down."
- id: 6
  start_time: 21.100
  end_time: 23.700
  text: "But give me a sign one more time, God."
- id: 7
  start_time: 24.220
  end_time: 28.960
  text: "John the Baptist, he devotes his life to preparing the way for Jesus."
- id: 8
  start_time: 29.420
  end_time: 34.840
  text: "And John the Baptist looks on to Jesus, he says, hey Jesus, I knew you were the one."
- id: 9
  start_time: 35.610
  end_time: 37.970
  text: "Now, I'm not so sure."
- id: 10
  start_time: 38.840
  end_time: 41.760
  text: "And then there's Thomas, doubting Thomas."
- id: 11
  start_time: 42.180
  end_time: 46.040
  text: "who says to Jesus after the resurrection, Jesus is raised from the dead."
- id: 12
  start_time: 46.040
  end_time: 53.080
  text: "And Thomas says, Jesus, I won't believe unless I see it with my own eyes."
- id: 13
  start_time: 54.150
  end_time: 1:04.090
  text: "It's strangely comforting to me to see the people in the Bible that were full of faith also occasionally battling with faith questions."
- id: 14
  start_time: 1:05.410
  end_time: 1:08.760
  text: "And it reminds us of really, really good news."
- id: 15
  start_time: 1:09.500
  end_time: 1:17.720
  text: "If you ever find yourself doubting or struggling just a little bit, it shows us doubting doesn't make you bad."
- id: 16
  start_time: 1:18.400
  end_time: 1:19.560
  text: "It makes you human."
- id: 17
  start_time: 1:20.680
  end_time: 1:29.200
  text: "It makes you human, like you're you're you're flawed and we're broken and and we are tainted by sin pursuing a good and a loving God."
- id: 18
  start_time: 1:29.460
  end_time: 1:35.450
  text: "And my favorite example that really gives me a sense of like relief and hope uh is what happened after Jesus gave his life."
- id: 19
  start_time: 1:39.220
  end_time: 1:46.570
  text: "When he was risen from the dead and right before what's known as the Ascension when he ascended into heaven, which would have been really 
cool."
- id: 20
  start_time: 1:47.130
  end_time: 1:49.260
  text: "I just kind of imagine how did he do it?"
- id: 21
  start_time: 1:49.590
  end_time: 1:53.940
  text: "Was it kind of like Jesus is standing there and it's kind of like a he's about to ascend and it's kind of like a"
- id: 22
  start_time: 1:55.100
  end_time: 1:55.840
  text: "[whoosh]"
- id: 23
  start_time: 1:56.370
  end_time: 1:58.150
  text: "I mean, I don't know, but that would be cool."
- id: 24
  start_time: 1:59.010
  end_time: 2:00.830
  text: "Right? I mean, just think about it."
  """

@pytest.fixture
def sample_srt():
    return "1\n00:00:00,000 --> 00:00:04,320\nYou've done miracles before, but we're not sure you can do them again.\n\n2\n00:00:04,320 --> 00:00:06,820\nWe're not sure we trust you now.\n\n3\n00:00:07,680 --> 00:00:09,500\nGideon, he's like me.\n\n4\n00:00:09,500 --> 00:00:13,880\nHe's like, hey God, if you're really with me, prove it again, one more time.\n\n5\n00:00:17,130 --> 00:00:20,840\nI know you've been faithful the last 47 times you've never let me down.\n\n6\n00:00:21,100 --> 00:00:23,700\nBut give me a sign one more time, God.\n\n7\n00:00:24,220 --> 00:00:28,960\nJohn the Baptist, he devotes his life to preparing the way for Jesus.\n\n8\n00:00:29,420 --> 00:00:34,840\nAnd John the Baptist looks on to Jesus, he says, hey Jesus, I knew you were the one.\n\n9\n00:00:35,610 --> 00:00:37,970\nNow, I'm not so sure.\n\n10\n00:00:38,840 --> 00:00:41,760\nAnd then there's Thomas, doubting Thomas.\n\n11\n00:00:42,180 --> 00:00:46,040\nwho says to Jesus after the resurrection, Jesus is raised from the dead.\n\n12\n00:00:46,040 --> 00:00:53,080\nAnd Thomas says, Jesus, I won't believe unless I see it with my own eyes.\n\n13\n00:00:54,150 --> 00:01:04,090\nIt's strangely comforting to me to see the people in the Bible that were full of faith also occasionally battling with faith questions.\n\n14\n00:01:05,410 --> 00:01:08,760\nAnd it reminds us of really, really good news.\n\n15\n00:01:09,500 --> 00:01:17,720\nIf you ever find yourself doubting or struggling just a little bit, it shows us doubting doesn't make you bad.\n\n16\n00:01:18,400 --> 00:01:19,560\nIt makes you human.\n\n17\n00:01:20,680 --> 00:01:29,200\nIt makes you human, like you're you're you're flawed and we're broken and and we are tainted by sin pursuing a good and a loving God.\n\n18\n00:01:29,460 --> 00:01:35,450\nAnd my favorite example that really gives me a sense of like relief and hope uh is what happened after Jesus gave his life.\n\n19\n00:01:39,220 --> 00:01:46,570\nWhen he was risen from the dead and right before what's known as the Ascension when he ascended into heaven, which would have been really cool.\n\n20\n00:01:47,130 --> 00:01:49,259\nI just kind of imagine how did he do it?\n\n21\n00:01:49,590 --> 00:01:53,940\nWas it kind of like Jesus is standing there and it's kind of like a he's about to ascend and it's kind of like a\n\n22\n00:01:55,100 --> 00:01:55,840\n[whoosh]\n\n23\n00:01:56,370 --> 00:01:58,150\nI mean, I don't know, but that would be cool.\n\n24\n00:01:59,009 --> 00:02:00,830\nRight? I mean, just think about it.\n\n"

def test_yaml_to_srt(sample_yaml, sample_srt):
    srt = _yaml_to_srt(sample_yaml)
    assert srt == sample_srt

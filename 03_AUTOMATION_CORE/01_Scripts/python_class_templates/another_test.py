import datetime


now = datetime.datetime.now()

print("Current Date and time is:")

print(now.strftime("%y-%m-%d %H:%M%S"))


import androidhelper

d=androidhelper.Android()
def speak(string):
    d.ttsSpeak(string)
    
''''''
1 = speak
2 = print


s = 1("Set, ")
s = 2("Set, ")

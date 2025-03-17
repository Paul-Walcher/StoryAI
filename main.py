
#importing the used modules
import ollama
import json
import os
import tiktoken
import re
import pprint

#own module imports
from ascii import *
from commands import *


#constants
PROMPT_SIGN: str = '>>>'
CURRENT_DIRECTORY: str = None

MODEL = None
MAX_TOKENS = None
AUTO_LOAD = False
MAX_FACT_SIZE = None
FACT_LIFESPAN = None

MEMORY = None
NARRATOR = None

FACT_REFS = {} #triggername: name
FACTS = {} #saved as {name: {content: , rank:} }

HISTORY = []#the global history

ARTIFACTS = []



LAST_AI_MSG = ""
#0: The Narrator info
#1: The Memory
#2-N The facts 
#rest: conversation




def create_files(fname: str) -> None:

	#creates all files inside the directory

	with open(os.path.join(fname, "memory.json"), "w") as memo:

		memo.write(
					r'''
{
	"memory": "" 
}
					'''	

				)

	with open(os.path.join(fname, "narrator.json"), "w") as narrator:

		narrator.write(
					r'''
{
	"narrator": "" 
}
					'''	

				)

	with open(os.path.join(fname, "facts.json"), "w") as facts:

		facts.write(

r'''
{
	"facts": [

				]
}
'''
			)

	with open(os.path.join(fname, "history.json"), "w") as story:

		story.write(

r'''
{
	"history": [


				]
}
'''

			)

	with open(os.path.join(fname, "settings.json"), "w") as settings:

		settings.write(

r'''
{
	
	"model": "deepseek-r1",
	"max_tokens": 64000,
	"auto_load": true,
	"max_fact_size": 4000,
	"fact_lifespan": 30

}
'''


)




def create_directory() -> bool:

	#returns true if the process was successfull, False if not
	
	freshprint("Enter the path where you want to create the directory: ", header=DIRECTORY, end="")

	dirpath: str = input()

	if not os.path.isdir(dirpath):

		freshprint("The directory does not exist!", header=DIRECTORY)
		input()
		return False

	freshprint("Enter the name of the directory: ", header=DIRECTORY, end="")
	name = input()

	#now creating the directory and instantly playing in it

	fname = os.path.join(dirpath, name)

	os.mkdir(fname)
	CURRENT_DIRECTORY = fname

	#now creating the files

	create_files(fname)

	return True

def introduction() -> None:

	global CURRENT_DIRECTORY

	#introduces via selecting a directory
	finished: bool = False

	while not finished:

		clear()

		print(INTRODUCTION)
		print()
		print(PROMPT_SIGN, "Enter the path to your directory, or enter /makedir to create one: ", end="")
		ans = input()

		if (ans == '/makedir'):

			succ: bool = create_directory()

			if succ:

				finished = True

			else:

				freshprint(PROMPT_SIGN + " The process failed!", header=INTRODUCTION)
				input()

		else:

			#check if the directory exists
			if (not os.path.exists(ans)):

				freshprint(PROMPT_SIGN + " The directory does not exist!", header=INTRODUCTION)
				input()

			else:

				
				CURRENT_DIRECTORY = os.path.abspath(ans)

				finished = True


def load_settings() -> None:

	#loads the setting
	global MODEL
	global MAX_TOKENS
	global AUTO_LOAD
	global MAX_FACT_SIZE
	global FACT_LIFESPAN

	with open(os.path.join(CURRENT_DIRECTORY, "settings.json")) as f:

		data = json.load(f)

		MODEL = data["model"]
		MAX_TOKENS = data["max_tokens"]
		AUTO_LOAD = data["auto_load"]
		MAX_FACT_SIZE = data["max_fact_size"]
		FACT_LIFESPAN = data["fact_lifespan"]

def load_history() -> None:

	global CURRENT_DIRECTORY
	#loads up the story if auto load is on

	with open(os.path.join(CURRENT_DIRECTORY, "history.json")) as f:

		data = json.load(f)

		history = data['history'] if data['history'] else []

		return history

def load_in_facts():

	global CURRENT_DIRECTORY
	global HISTORY
	global FACTS
	global FACT_REFS

	#loads in all facts based on the chat history
	with open(os.path.join(CURRENT_DIRECTORY, "facts.json")) as facts:

		data = json.load(facts)

		factarr = data["facts"]

		if factarr:

			for fact in factarr:

				FACTS[fact["name"]] = {"content": fact["content"], "rank": fact["rank"]}

				for name in fact["triggers"]:

					FACT_REFS[name] = fact["name"]








def manage_history(load_history):

	global CURRENT_DIRECTORY
	global HISTORY
	global MEMORY
	global NARRATOR


	if not HISTORY:
		#fill the history
		with open(os.path.join(CURRENT_DIRECTORY, "narrator.json")) as f:

			data = json.load(f)

			NARRATOR = {"role": "user", "content": data["narrator"]}

		with open(os.path.join(CURRENT_DIRECTORY, "memory.json")) as f:

			data = json.load(f)

			MEMORY = {"role": "user", "content": data["memory"]}


		load_in_facts()

		HISTORY.extend(load_history)


def find_triggers(message: str) -> list[str]:


	found_triggers: list[str] = []

	for trigger in FACT_REFS:

		if re.match(".*" + trigger + ".*", message, re.IGNORECASE):

			found_triggers.append(FACT_REFS[trigger])

	return found_triggers

def resize(post: list):

	"""
	resizes the post to fit into the token limit
	"""

	enc = tiktoken.get_encoding("cl100k_base") 

	size = 0

	for comment in post:

		size += len(enc.encode(comment["content"]))

	if size > MAX_TOKENS:

		#we need to shrink it down

		overflow = MAX_TOKENS - size

		count = 0
		post_index = 2

		while post_index < len(post) and count < overflow:

			count += len(enc.encode(post[post_index]["content"]))
			post_index += 1

		to_delete = post_index - 2

		for i in range(to_delete):
			post.pop(2)

	return post

def cut_memory():

	global HISTORY

	post = [NARRATOR] + [MEMORY] + HISTORY
	"""
	resizes the post to fit into the token limit
	"""

	enc = tiktoken.get_encoding("cl100k_base") 

	size = 0

	for comment in post:

		size += len(enc.encode(comment["content"]))

	if size > MAX_TOKENS:

		#we need to shrink it down

		overflow = MAX_TOKENS - size

		count = 0
		post_index = 2

		while post_index < len(post) and count < overflow:

			count += len(enc.encode(post[post_index]["content"]))
			post_index += 1

		to_delete = post_index-2

		for i in range(to_delete):
			HISTORY.pop(0)

	return post

def save_data():

	data = {"history": HISTORY}

	with open(os.path.join(CURRENT_DIRECTORY, "history.json"), "w") as f:

		print(data)
		json.dump(data, f)

def reload_memory():

	global MEMORY

	with open(os.path.join(CURRENT_DIRECTORY, "memory.json")) as f:

		data = json.load(f)
		MEMORY = {"role": "user", "content": data["memory"]}

def reload_narrator():

	global NARRATOR

	with open(os.path.join(CURRENT_DIRECTORY, "narrator.json")) as f:

		data = json.load(f)
		NARRATOR = {"role": "user", "content": data["narrator"]}



if __name__ == "__main__":

	running = True

	while running:

		#starting the introduction

		introduction()

		#loading the setting
		load_settings()
		#now we have the current directory, now start up the AI
		history = load_history()

		clear()

		talking: bool = True

		while talking:

			genfacts = False
			gensummary = False

			manage_history(history)

			message = input(">>> ")

			if (message == "/exit"):

				running = False
				talking = False
				save_data()
				break

			if (message == "/switch"):

				talking = False
				save_data()
				break

			if (message == "/reload_facts"):

				load_in_facts()
				continue

			if (message == "/reload_memory"):

				reload_memory()
				continue

			if (message == "/reload_narrator"):

				reload_narrator()
				continue

			if (message == "/memory"):

				print("\n\n"+MEMORY+"\n\n")
				continue

			if (message == "/narrator"):

				print("\n\n"+NARRATOR+"\n\n")
				continue

			if (message == "/generate_facts"):

				genfacts = True

			if (message == "/summary"):

				gensummary = True

			if (message == "/memory_size"):

				post = [NARRATOR] + [MEMORY] + HISTORY

				enc = tiktoken.get_encoding("cl100k_base") 

				size = 0

				for comment in post:

					size += len(enc.encode(comment["content"]))

				print("\n\n"+str(size)+"\n\n")

				continue

			if (message == "/cut_memory"):

				cut_memory()
				continue






			#now creating the message


			#now editing the new facts in
			fact_triggers = find_triggers(message)
			fact_triggers.extend(find_triggers(LAST_AI_MSG))
			#finding all facts
			#then providing them

			text = ""

			if fact_triggers:

				text += "Here are some extra facts about the world or/and environment."\
						"They will be listed as: corrsponding name: Information, then four empty lines.\n\n"

				for fact in fact_triggers:

					text += fact + ": " + FACTS[fact]["content"] + "\n\n\n\n"

			message = text + message

			if (genfacts):

				message = "Now, I ask you to generate facts based upon important objects or characters in the story."\
						"I would like you to generate the facts in a python list, where each element is a dictionary with the contents:"\
						'"name": The name of the fact/person/object as a string, "content": The description of the object/person/thing'\
						'"triggers": A list of names that trigger remembering the object. For example, when I have a sword as a fact,'\
						'the fact should be triggered by "fight", "sword", "weapon", usw. Finally there is: "rank", from 1-1000,'\
						'where the higher the number the higher the importance of the fact. All facts are used to feed an AI whenever the trigger'\
						'words are mentioned, either by the AI or by the user. The AI will then receive the content to remember the object/thing/person.'

			if (gensummary):

				message = "Now, please generate a summary of what has happened so far."

			HISTORY.append({"role": "user", "content": message})

			post = [NARRATOR] + [MEMORY] + HISTORY


			#now chugging old messages

			post = resize(post)


			stream = ollama.chat(
						    model=MODEL,
						    messages=post,
						    stream=True,
						    options={"num_ctx": MAX_TOKENS}
						)

			answer = ""
			for chunk in stream:
				answer += chunk['message']['content']
			
			print("\n\n" + answer + "\n\n")

			LAST_AI_MSG = answer

			HISTORY.append({"role": "assistant", "content": answer})

		




	clear()





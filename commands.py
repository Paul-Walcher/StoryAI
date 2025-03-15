"""
Collection of useful commands
"""

import os
import platform


#determining the platform

operating_system: str = platform.system()



def clear() -> None:

	"""
	Clears the screen
	"""

	if (operating_system == "Windows"): os.system("cls")
	elif (operating_system == "Linux"): os.system("clear")
	elif (operating_system == "Darwin"): os.system("clear")

def freshprint(text: str, prompt_sign=">>> ", header=None, end="\n") -> None:

	#prints from a fresh line

	clear()

	if header is not None:

		print(header)
		print()

	print(text, end=end)




import os
import json
from .DecimalEncoder import DecimalEncoder
from .Logger import Logger
from functools import reduce
import csv


class Utils(object):

	base_folder = "/tmp/cache_data/"

	@staticmethod
	def get_output_file_name_old(school_code, class_name, stu_uuid, mode, term_name):
		f1 = os.path.join( Utils.base_folder, school_code,  class_name, mode)
		if  not os.path.exists(f1): # os.path.isdir(f1):
			os.makedirs(f1)
		file_name = os.path.join( f1 , stu_uuid + "-"  + term_name + ".json")
		return file_name
	
	@staticmethod
	def get_output_folder_name(*other_paths, add_base_folder = True):
		#print(other_paths)
		f2 = ""
		for p in other_paths:
			f2 = os.path.join( f2, p)
		#print(f2)
		#exit()
		#f1 = os.path.join( Utils.base_folder, other_paths)
		if add_base_folder:
			f1 = os.path.join( Utils.base_folder, f2)
		else:
			f1 = f2
		if  not os.path.exists(f1): # os.path.isdir(f1):
			os.makedirs(f1)
		#file_name = os.path.join( f1 , stu_uuid + "-"  + term_name + ".json")
		return f1

	@staticmethod
	def get_output_file_name(folder_path, file_name):
		f1 = folder_path # os.path.join( Utils.base_folder, school_code,  class_name, mode)
		if  not os.path.exists(f1): # os.path.isdir(f1):
			os.makedirs(f1)
		file_name = os.path.join( f1 , file_name)
		return file_name

	@staticmethod
	def save_json(file_name, data):
		#print(data)
		#exit()
		with open(file_name, 'w') as f_out:
			json.dump(data, f_out, cls=DecimalEncoder, indent=5)
    
		# Closing file
		f_out.close()

	@staticmethod
	def load_json(file_name, return_empty_array = True):
		data = list()
		if not os.path.isfile(file_name):
			Logger.print(file_name, "is missing... returning empty list array")
			if return_empty_array:
				return data
			else:
				return None
		with open(file_name, 'r', encoding="utf8") as f_out:
			data = json.load(f_out)
		# Closing file
		f_out.close()
		return data
	

	@staticmethod
	def unique(list):
		unique_list = reduce(lambda re, x: re+[x] if x not in re else re, list, [])
		return unique_list

	@staticmethod
	def csv_to_json(csvFilePath):
		data = []  # Initialize an empty dictionary

		with open(csvFilePath, encoding='utf-8') as csvf:
			csvReader = csv.DictReader(csvf, delimiter=',')  # Read the CSV file using DictReader
			print(csvReader)
			#exit()
			for row in csvReader:
				data.append(row)
				
		return data
	
	@staticmethod
	def save_text_to_file(file_name, txt:str):
		# Open a file in write mode
		with open(file_name, 'w', encoding="utf8") as file:
			# Write a string to the file
			file.write(txt)

	@staticmethod
	def save_to_file(file_name, bytes):
		# Open a file in write mode
		with open(file_name, 'wb') as file:
			# Write a string to the file
			file.write(bytes)

	@staticmethod
	def read_static_file(file_name):
		# Read the content of the "system_card.txt" file
		with open(file_name, "r") as file:
			file_contents = file.read()
		
		return file_contents

import sys
import os
import shutil
import subprocess
import requests
import configparser
import json
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import tkinter as tk
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
from tkinter import filedialog
import re

class FileAddedHandler(FileSystemEventHandler):
    def __init__(self, app, test):
        self.app = app
        self.project_path = test['project_path']
        self.folder_path = test['folder_path']
        self.server_url = test['server_url']
        self.file_extension = test['file_extension']
        self.folder_pass = test['folder_pass']
        self.folder_fail = test['folder_fail']
        self.parallelStation = test['parallelStation']

    def on_created(self, event):
        if event.is_directory:
            return
        else:
            file_path = event.src_path
            self.process_information(file_path)

    def process_existing_files(self):
        for filename in os.listdir(self.folder_path):
            
            file_path = os.path.join(self.folder_path, filename)
            self.process_information(file_path)

    def process_information(self, file_path):
        file_extension = os.path.splitext(file_path)[1]
        if file_extension.lower() == self.file_extension.lower():
            file_basename = os.path.basename(file_path)
            file_name_without_ext = os.path.splitext(file_basename)[0]
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            split_filename = file_name_without_ext.split("_")
            if len(split_filename) == 4:
                serial_number = split_filename[1] #satu
                datetime_str = split_filename[2] + split_filename[3]
                datetime_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                formatted_timestamp = datetime_obj.strftime('%Y-%m-%d %H:%M:%S') #dua
                if os.path.isdir(self.folder_path):
                    success = os.path.basename(self.folder_path) #tiga
                [result, description] = self.app.send_file_to_server(self.server_url, file_basename, serial_number, formatted_timestamp, success, self.parallelStation)
                # [result, description] =[True, 'COMPLETED']

                if success == 'PASS':
                    if result == True or result == False:
                        # Move to pass folder
                        move_folder = self.folder_pass
                        os.makedirs(move_folder, exist_ok=True)
                        shutil.move(file_path, os.path.join(move_folder, file_basename))
                        print("result : ", result)
                        if result == True:
                            self.app.add_file_to_listbox(f"  {timestamp}  |  PASS |  {serial_number}  |  COMPLETED")
                            description = f"{timestamp}  |  PASS  |  {serial_number}  |  {description}\n"
                        else:
                            self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL  |  {serial_number}  |  {description}", "red")
                            description = f"{timestamp}  |  FAIL  |  {serial_number}  |  {description}\n"

                        filename = self.project_path + '/log.txt'
                        self.update_log(filename, description)

                    else:
                        self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL   |  {file_name_without_ext}  |  Error POST {file_name_without_ext} to server, file not move", "red")
                elif success == 'FAIL':
                    if result == True or result == False:            
                        # Move to pass folder
                        move_folder = self.folder_pass
                        os.makedirs(move_folder, exist_ok=True)
                        shutil.move(file_path, os.path.join(move_folder, file_basename))
                        self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL  |  {serial_number}  |  {description}", "red")

                        filename = self.project_path + '/log.txt'
                        description = f"{timestamp}  |  FAIL  |  {serial_number}  |  {description}\n"

                        self.update_log(filename, description)
                    else:
                        self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL   |  {file_name_without_ext}  |  Error POST {file_name_without_ext} to server, file not move", "red")
                else:
                    self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL   |  {file_name_without_ext}  |  Error: Not in PASS / FAIL folder, file not move", "red")
            else:
                self.app.add_error_to_listbox(f"  {timestamp}  |  FAIL   |  {file_name_without_ext}  |  Error: Not a valid format name, ignored", "red")
    
    def update_log(self, filename, description):
        if not os.path.isfile(filename):
            with open(filename, 'w') as file:
                file.write(f"Log of FCT Test.\n\n")

        with open(filename, 'a+') as file:
            file.write(description)


class MonitorApp:
    def __init__(self):
        self.station_name = ""
        self.folder_path = ""
        self.root = tk.Tk()
        self.varNeedChecking = tk.IntVar()
        self.root.title("FCT LogFile Monitoring ( Version : MSA-a354d7aa )")
        self.create_widgets()
        self.apiStationInfo = ""
        self.epwiPath = ""
        self.processEpwi = None

    def create_station_info_textbox(self):

        # label for input
        self.project_label = tk.Label(self.root, text="PROJECT NAME")
        self.project_label.grid(row=0, column=5, padx=4, pady=5)
        self.fileExt_label = tk.Label(self.root, text="FILE EXTENSION")
        self.fileExt_label.grid(row=0, column=7, padx=4, pady=5)
        self.mainStation_label = tk.Label(self.root, text="MAIN STATION")
        self.mainStation_label.grid(row=1, column=5, padx=4, pady=5)
        self.parallelStation_label = tk.Label(self.root, text="PARALLEL STATION")
        self.parallelStation_label.grid(row=1, column=7, padx=4, pady=5)
        self.server_label = tk.Label(self.root, text="API SERVER LINK")
        self.server_label.grid(row=2, column=5, padx=4, pady=5)
        self.path_choose_button = tk.Button(self.root, text="MONITOR FOLDER", command=self.choose_folder)
        self.path_choose_button.grid(row=3, column=5, padx=4, pady=5)

        # input by text
        self.input_field_project = ttk.Combobox(self.root)
        self.input_field_project = ttk.Combobox(self.root, state='readonly')
        self.input_field_project.configure(width=22)
        self.input_field_project.grid(row=0, column=6, padx=15, pady=7)
        self.getProjectList() #to request data for this select option
        self.input_field_project.bind("<<ComboboxSelected>>", self.on_change_project)

        self.input_field_file_ext = tk.Entry(self.root)
        self.input_field_file_ext.insert(0, ".log")
        self.input_field_file_ext.config(state=tk.DISABLED)
        self.input_field_file_ext.configure(width=8)
        self.input_field_file_ext.grid(row=0, column=8, padx=15, pady=7)

        self.input_field_mainStation = ttk.Combobox(self.root)
        self.input_field_mainStation = ttk.Combobox(self.root, state='readonly')
        self.input_field_mainStation.configure(width=22)
        self.input_field_mainStation.grid(row=1, column=6, padx=15, pady=7)
        self.input_field_mainStation.bind("<<ComboboxSelected>>", self.on_change_station)

        self.input_field_parallelStation = ttk.Combobox(self.root)
        self.input_field_parallelStation = ttk.Combobox(self.root, state='readonly')
        self.input_field_parallelStation.configure(width=5)
        self.input_field_parallelStation.grid(row=1, column=8, padx=15, pady=7)
        self.input_field_parallelStation.bind("<<ComboboxSelected>>")
        
        self.input_field_server = tk.Entry(self.root)
        self.input_field_server.configure(width=64)
        self.input_field_server.config(state=tk.DISABLED)
        self.input_field_server.grid(row=2, column=6, columnspan=3, padx=15, pady=7)

        self.update_text(self.folder_path)

        self.needCheckingBefore = tk.Checkbutton(self.root, text="CHECK BEFORE FCT", variable=self.varNeedChecking, command=self.on_checkbox_change)
        self.needCheckingBefore.grid(row=0, column=9,padx=15, pady=8)

        # button start and stop
        self.start_button = tk.Button(self.root, text="START", bg="red", command=self.handle_start_button)
        self.start_button.grid(row=1, column=9, rowspan=2, padx=15, pady=8)
        self.start_button.configure(width=17, height=5)

        self.stop_button = tk.Button(self.root, text="STOP", command=self.handle_stop_button)
        self.stop_button.grid(row=3, column=9, padx=15, pady=8)
        self.stop_button.configure(width=17, height=2)

    def create_check_station(self):

        label_font = font.Font(size=12)
        label_font2 = font.Font(size=18)
        # label for input
        self.scan_label = tk.Label(self.root, text="SERIAL NUMBER")
        self.scan_label.grid(row=0, column=0, padx=4, pady=5)

        # input by text
        self.input_serial_number = tk.Entry(self.root, font=label_font2, state='readonly')
        # self.input_serial_number.insert(0, "234567890-678-2-67")
        self.input_serial_number.grid(row=1, column=0, columnspan=5, rowspan=2, padx=15, pady=7)
        self.input_serial_number.configure(width=40)
        self.input_serial_number.bind("<Return>", self.handle_barcode)
        
        self.listbox_check_label  = tk.Label(self.root, text="Check Before Transaction:", font=label_font)
        self.listbox_check_label .grid(row=5, column=0, columnspan=5, padx=10, pady=20)

        self.check_listbox = tk.Listbox(self.root, width=100, height=20)
        self.check_listbox.grid(row=6, column=0, columnspan=5, padx=15, pady=20)

    
    def update_text(self, folder_path):

        self.station_info_textbox = tk.Text(self.root, height=4)
        self.station_info_textbox.configure(width=48)
        if self.folder_path:
            self.station_info_textbox.insert(tk.END, f" {folder_path}/PASS \n")
            self.station_info_textbox.insert(tk.END, f" {folder_path}/FAIL \n")
        self.station_info_textbox.config(state=tk.DISABLED)
        self.station_info_textbox.grid(row=3, column=6, columnspan=3)

    def create_widgets(self):
        self.create_station_info_textbox()
        label_font = font.Font(size=12)
        self.listbox_label  = tk.Label(self.root, text="FCT Transaction:", font=label_font)
        self.listbox_label .grid(row=5, column=5, columnspan=5, padx=10, pady=20)

        self.listbox = tk.Listbox(self.root, width=100, height=20, xscrollcommand=True)
        self.listbox.grid(row=6, column=5, columnspan=5, padx=15, pady=20)

    def choose_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.update_text(folder_path)

    def send_file_to_server(self, server_url, file_basename, file_name_without_ext, timestamp, status, parallelStation):
        try:
            
            data={
                "logFileName": file_basename,
                "mainStation": self.station_name,
                "serialNumber": file_name_without_ext,
                "status": status,
                "parallelStation": parallelStation
            }
            headers = {'Content-type': 'application/json'}
            response = requests.post(server_url, json.dumps(data), headers=headers)
            _response = json.loads(response.content.decode())
            result = _response[0]['success']
            description = _response[0]['description']
            return [result, description]
        except requests.exceptions.RequestException as e:
            print(f"Error POST file to server: {e}")
            return False

    def add_file_to_listbox(self, file_name):
        if self.listbox.size() == 50:
            self.listbox.delete(49)
        self.listbox.insert(0, file_name)
        self.listbox.itemconfig(0, fg="white")
        self.listbox.itemconfig(0, bg="darkgreen")
        bolded = font.Font(size=10, weight='bold')
        self.listbox.config(font=bolded)
        self.listbox.yview(0)

    def add_error_to_listbox(self, error_message, color):
        if self.listbox.size() == 50:
            self.listbox.delete(49)
        self.listbox.insert(0, error_message)
        self.listbox.itemconfig(0, fg="white")
        self.listbox.itemconfig(0, bg=color)
        bolded = font.Font(size=10, weight='bold')
        self.listbox.config(font=bolded)
        self.listbox.yview(0)

    def getProjectList(self):
        
        server_url = "http://192.168.0.28/final_line_Q42023/"
        url = server_url + "dgs/general_ReadProjectList.php"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            project_list = data['projectName']

            self.input_field_project['values'] = project_list
        else:
            print("Error:", response.status_code)
            
    def on_change_project(self, event):
        selected_project = self.input_field_project.get()
        self.getApiByProject(selected_project)
            
    def on_change_station(self, event):
        selected_station = self.input_field_mainStation.get()
        self.station_name = selected_station
        self.getStationInformationByStationName(self.apiStationInfo, selected_station)

    def on_checkbox_change(self):
        if self.varNeedChecking.get() == 1: 
            self.create_check_station()
        else:
            self.scan_label.grid_forget()
            self.input_serial_number.grid_forget()
            self.listbox_check_label.grid_forget()
            self.check_listbox.grid_forget()
            self.view_result.grid_forget()

    def handle_barcode(self, event):
        # Check if the barcode scanner's input is complete (e.g., Enter key pressed)
        if event.keysym == "Return":
            serial_number = self.input_serial_number.get()
            main_station = self.station_name
            match = re.search(r'__(\d+)', main_station)
            if match:
                number = int(match.group())
                main_station = 'CHECKB4FCT__' + number
            else:
                main_station = 'CHECKB4FCT'
            parallel_station = self.input_field_parallelStation.get()
            server_url = self.input_field_server.get()
            try:
                data={
                    "serialNumber": serial_number,
                    "mainStation": main_station,
                    "parallelStation": parallel_station,
                    "status": 'PASS',
                }
                headers = {'Content-type': 'application/json'}
                response = requests.post(server_url, json.dumps(data), headers=headers)
                _response = json.loads(response.content.decode())
                result = _response[0]['success']
                description = _response[0]['description']
                label_font3 = font.Font(size=23)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                if result:
                    self.view_result = tk.Label(self.root, text="PASS TO PROCEED, CONTINUE FCT TEST", font=label_font3, bg="green", fg="white")
                    self.view_result.grid(row=3, column=0, columnspan=5, rowspan=2, padx=4, pady=5)
                    self.view_result.configure(width=35)

                    self.add_check_to_listbox(f"  {timestamp}  | PASS |  {serial_number}  |  PROCEED")
                else:
                    self.view_result = tk.Label(self.root, text="FAIL TO PROCEED, STOP/SKIP FCT TEST", font=label_font3, bg="red", fg="white")
                    self.view_result.grid(row=3, column=0, columnspan=5, rowspan=2, padx=4, pady=5)
                    self.view_result.configure(width=35)
                    self.add_error_check_to_listbox(f"  {timestamp}  | FAIL  |  {serial_number}  |  {description}", "red")

            except requests.exceptions.RequestException as e:
                print(f"Error POST file to server: {e}")
                return False

    def add_check_to_listbox(self, file_name):
        if self.check_listbox.size() == 50:
            self.check_listbox.delete(49)
        self.check_listbox.insert(0, file_name)
        self.check_listbox.itemconfig(0, fg="white")
        self.check_listbox.itemconfig(0, bg="darkgreen")
        bolded = font.Font(size=10, weight='bold')
        self.check_listbox.config(font=bolded)
        self.check_listbox.yview(0)

    def add_error_check_to_listbox(self, error_message, color):
        if self.check_listbox.size() == 50:
            self.check_listbox.delete(49)
        self.check_listbox.insert(0, error_message)
        self.check_listbox.itemconfig(0, fg="white")
        self.check_listbox.itemconfig(0, bg=color)
        bolded = font.Font(size=10, weight='bold')
        self.check_listbox.config(font=bolded)
        self.check_listbox.yview(0)

    def getApiByProject(self, project):
        server_url = "http://192.168.0.28/final_line_Q42023/"
        url = server_url + "dgs/general_ReadProjectList.php?projectName="+project
        self.input_field_server.config(state=tk.NORMAL)
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            apiServer = data['apiS'][0]
            stationInfoApi = data['apiS'][1]
            epwiPath = data['apiS'][2] + 'FCT'
            # getStationInfo
            
            self.apiStationInfo = stationInfoApi
            self.epwiPath = epwiPath
            self.getStationNameList(stationInfoApi)

            # update api server
            self.input_field_server.delete(0, tk.END)  # Clear the current value
            self.input_field_server.insert(0, apiServer)  # Set the new value
            self.input_field_server.config(state=tk.DISABLED)
            
        else:
            print("Error:", response.status_code)

    def getStationNameList(self, stationInfoApi):
        # self.input_field_server.config(state=tk.NORMAL)
        response = requests.get(stationInfoApi+'?stationLike=FCT')
        print("API use: ", stationInfoApi+'?stationLike=FCT')
        if response.status_code == 200:
            data = response.json()
            stationNameArray = data['result']
            self.input_field_mainStation['values'] = stationNameArray
            self.input_field_mainStation.current(0)
            self.getStationInformationByStationName(stationInfoApi, stationNameArray[0])
            self.station_name = stationNameArray[0]
            
        else:
            print("Error:", response.status_code)


    def getStationInformationByStationName(self, stationInfoApi, stationName):
        
        # self.input_field_server.config(state=tk.NORMAL)
        response = requests.get(stationInfoApi+'?stationName='+stationName)
        print("API use: ", stationInfoApi+'?stationName='+stationName)
        if response.status_code == 200:
            data = response.json()
            
            parallelStationArray = []
            for i in range(1, int(data['result']) + 1):
                parallelStationArray.append(i)
            self.input_field_parallelStation['values'] = parallelStationArray
            self.input_field_parallelStation.current(0)
            
        else:
            print("Error:", response.status_code)

    def start_monitoring(self, serverApi, fileExt, parallelStation):
        
        path = self.folder_path
        event_handler = {}
        self.observer = Observer()
            
        setting_folder_pass = {
            'server_url': serverApi,
            'project_path' : path,
            'folder_path': path + '/PASS',
            'folder_pass': path + '/PASS/PASS_API',
            'folder_fail': path + '/PASS/FAIL_API',
            'file_extension': fileExt,
            'parallelStation' : parallelStation
        }
        setting_folder_fail = {
            'server_url': serverApi,
            'project_path' : path,
            'folder_path': path + '/FAIL',
            'folder_pass': path + '/FAIL/PASS_API',
            'folder_fail': path + '/FAIL/FAIL_API',
            'file_extension': fileExt,
            'parallelStation' : parallelStation
        }

        event_handler[0] = FileAddedHandler(self, setting_folder_pass)
        event_handler[1] = FileAddedHandler(self, setting_folder_fail)

        event_handler[0].process_existing_files()
        event_handler[1].process_existing_files()

        self.observer.schedule(event_handler[0], path + '/PASS', recursive=False)
        self.observer.schedule(event_handler[1], path + '/FAIL', recursive=False)
        
        self.observer.start()
        
        try:
            unc_path = self.epwiPath
            command = f'pushd {unc_path} && epwi.exe'
            if len(unc_path) > 10:
                self.processEpwi = subprocess.Popen(command, shell=True)
        except:
            pass
        
    def stop_monitoring_and_quit(self):
        self.observer.stop()
        self.observer.join()
        self.root.quit()

    def handle_start_button(self):

        if (self.input_field_server.get() != '' and  self.input_field_file_ext.get() != '' and  self.input_field_parallelStation.get() != '' and self.folder_path != ''):
            self.input_field_project['state'] = "disable"
            self.input_field_server['state'] = "disable"
            self.path_choose_button['state'] = "disable"
            self.station_info_textbox['state'] = "disable"
            self.input_field_parallelStation['state'] = "disable"
            self.input_field_mainStation['state'] = "disable"
            self.start_button['state'] = "disable"
            self.start_button['bg'] = "dark green"
            self.stop_button['state'] = "normal"
            self.needCheckingBefore['state'] = "disable"
            self.start_monitoring(self.input_field_server.get(), self.input_field_file_ext.get(), self.input_field_parallelStation.get())
            try:
                self.input_serial_number['state'] = "normal"
                self.input_serial_number.focus_set()
            except:
                pass

        else:
            messagebox.showinfo("Alert", "Please fill in all the input needed!")

    def handle_stop_button(self):
        self.input_field_project['state'] = "normal"
        self.input_field_server['state'] = "normal"
        self.path_choose_button['state'] = "normal"
        self.station_info_textbox['state'] = "normal"
        self.start_button['state'] = "normal"
        self.input_field_parallelStation['state'] = "normal"
        self.input_field_mainStation['state'] = "normal"
        self.start_button['bg'] = "red"
        self.stop_button['state'] = "disable"
        self.needCheckingBefore['state'] = "normal"
        self.observer.stop()
        self.observer.join()
        
        try:
            self.input_serial_number['state'] = "disable"
        except:
            pass
        
        try:
            unc_path = self.epwiPath
            if len(unc_path) > 10 :
                subprocess.run(['pushd', str(unc_path), '&&', 'taskkill', '/F', '/T', '/PID', str(self.processEpwi.pid)], shell=True)
        except:
            pass

    def run(self):
        self.root.mainloop()

class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr



if __name__ == "__main__":
    app = MonitorApp()
    app.run()

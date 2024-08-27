FCT Log Monitoring

Description:
Python's TKinter library to develop a standalone system that monitors changes in a designated folder after a log file has been generated upon completing the FCT test. The system is designed to track files with a specific format, such as .log files. Additionally, it will establish communication with the SQL Server located at 192.168.0.28 in order to update the FCT test results.

Concept:
1. Monitor existing files and on create file in the {path}/PASS and {path}/FAIL folder
2. Check log file will be moved to new path
3. System create new folder to move the file:
	- {path}/PASS/PASS_API 
	- {path}/PASS/FAIL_API	
	- {path}/FAIL/PASS_API 
	- {path}/FAIL/FAIL_API
4. Either pass or fail FCT test, system will update into server
	- if successfully update, file will be moved into .../PASS_API 	
	- if failed update, file will be moved into .../FAIL_API
5. Condition of file monitoring
        - only file with {file_extension} format will be monitor 
        - use our standard format name : FCT_{serial_number}_{YYYYMMDD}_{HHMMSS}.{file_extension}
6. System checking will create and update all log in log.txt file in {folder_path} + '/log.txt'

Step:
1. MODEL NAME : user need to choose model to run FCT test
2. API SERVER LINK : this input will be automatically update after choosing model
3. MONITOR FOLDER : user need to click this button and select the path where the log file created (outside PASS/FAIL folder)
4. Click button START and system will run or STOP to stop the system
5. Transaction textarea will update the list of log for each file monitoring sorted by the latest. Only GREEN background colour is considered passed to proceed next step

API Used:
1. http://192.168.0.28/getFctApi/getModelList.php - to get list of model
2. http://192.168.0.28/getFctApi/getModelList.php?model=... - to get api used for specific model
3. **Depend on selected model API

Database Information (used by the server, for reference only)
1. Server 	- 192.168.0.28
   Database - general_information
   Table 	- db.apiFct
2. **Depend on selected model API

Production Build:
1. Run command `pyinstaller --onefile .\FCT_monitoring.py --noconsole`



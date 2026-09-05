#!/usr/bin/python3

###################################################################
# podman volume backup script written in python.                  #
#                                                                 #
# Author: Marcus Uddenhed                                         #
# Version: 1.2.4                                                  #
# Date: 2026-09-05                                                #
# Requirements:                                                   #
# paramiko for SFTP functions, only if vSendToSftp is set to yes. #
#                                                                 #
###################################################################

## Global variables.
vBckDir: str = ""                     # Backup folder to use during creation of volume exports and to store files locally.
vFilePrefix: str = ""                 # Name prefix of files, _date and .tar is added at the end, ex. 'prefix_volumename_date.tar'.
vKeepBackup: str = "no"               # Keep local backup files after sent to SFTP server, if no than nothing is kept locally.(no/yes)
vKeepDays: str = "20"                 # Number of days to keep local files before pruning the backup directory, relies on vKeepBackup.
vSendToSftp: str = "no"               # Should we send the files to a Sftp server.(no/yes)
vSftpUser: str = ""                   # User for the remote server, used both with password or key file.
vSftpPass: str = ""                   # Password for the remote server.
vSftpUseKey: str = "no"               # Use key file as authenticator against remote server for SFTP.
vSftpKeyFile: str = ""                # Full path and key to use when connecting via key file instead of username/password.
vSftpDir: str = ""                    # Destination folder on remote server.
vSftpHost: str = ""                   # Remote server address.
vSftpPort: str = "22"                 # Remote server port.
vSftpTimeout: str = "0"               # Set SFTP timeout before failing, 0 sets it to None.
vPreBckCmd: str = "no"                # Run extra OS specific commands before backup.(no/yes)
vPostBckCmd: str = "no"               # Run extra OS specific commands after backup.(no/yes)

# External OS commands to execute before continuing with the rest of the script.
vPreOsCmd: list[str] = [""]

# External OS commands to execute at the end of the script.
vPostOsCmd: list[str] = [""]

# If you want to exclude or include volumes in backup you can use these two options.
# If both are empty it will do a backup of every volumes that exists.
# The include takes precedence over exclude pattern, so if you add to both the exclude lookup
# will be ignored, the words are CASE sensitive so "data" is not equal to "Data" and so on.
vIncludePattern: list[str] = [""]
vExcludePattern: list[str] = [""]

#### Do not edit anything below this line ####

## Module imports.
from datetime import datetime
from time import time
import subprocess
import os

# Convert to int to keep it tidy in user parameters.
vKeepDaysInt = int(vKeepDays)
vSftpPortInt = int(vSftpPort)

# Volume list command
vListCmd: str = "podman volume list --format {{.Name}}"

# Volume export command
vExportCmd: str = "podman volume export --output"

#### Script Action

## Import pysftp only if vSendToSftp set to yes.
if vSendToSftp.lower() == "yes":
  import paramiko

## Define global array for volume file names.
vGlobNameList: list[str] = []

## Get current date
def funcDateString() -> str:
  # Returns the today string year, month, day.
  return datetime.now().strftime("%Y%m%d")

## Define function for Pre OS commands.
def funcExecutePreOsCmd(vPreOsCmd: list[str]) -> None:
  try:
    if vPreBckCmd.casefold() == "yes":
      # iterate through each specified command.
      for vExecute in vPreOsCmd:
        _ = subprocess.run(vExecute, shell=True, check=True)
      # Send info to console.
      print("OS commands has been executed...")
  except:
    # Send info to console.
    print("Could not execute OS command...")

## Define function for Pre OS commands.
def funcExecutePostOsCmd(vPostOsCmd: list[str]) -> None:
  try:
    if vPostBckCmd.casefold() == "yes":
      # iterate through each specified command.
      for vExecute in vPostOsCmd:
        _ = subprocess.run(vExecute, shell=True, check=True)
      # Send info to console.
      print("OS commands has been executed...")
  except:
      # Send info to console.
      print("Could not execute OS command...")

## Define function for exporting volumes.
def funcExportVolumes() -> None:
  try:
    # Mark vGlobNameList global
    global vGlobNameList
    # Get volume names.
    vGetList = subprocess.run(vListCmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Create an array with the names.
    vNameList: list[str] = vGetList.stdout.decode('utf-8')[:-1].split('\n')
    # Iterate through volumes.
    for vName in vNameList:
      # Set to 0 as default(1 = Backup, 2 = Skip).
      vBackup: int = 0
      # Check to see if include or exclude is used.
      if (len(vIncludePattern[0]) == 0) and (len(vExcludePattern[0]) == 0):
        # Set to 1.
        vBackup = 1
      else:
        # Check if include is used.
        if (len(vIncludePattern[0]) != 0):
          # Iterate through include pattern.
          for vInc in vIncludePattern:
            # Check for match.
            if vInc in str(vName):
              # Set to 1.
              vBackup = 1
        # Check if exclude is used.
        elif (len(vExcludePattern[0]) != 0):
          # Iterate through exclude pattern.
          for vEx in vExcludePattern:
            # Check for match.
            if vEx in str(vName):
              # Set to 2.
              vBackup = 2
            else:
              # Only change if not set to 2.
              if vBackup != 2:
                # Set to 1.
                vBackup = 1
      # Do backup if equal to 1.
      if vBackup == 1:
        funcDoBackup(vName.encode('utf-8'))
        # Send to output.
        vEncName: str = vName
        print("Volume exported: ", vEncName)
  except:
    # Send info to console.
    print("Could not export one or more volumes...")

## Define backup function
def funcDoBackup(vInputName: bytes) -> None:
  # Build filename.
  vSetTarFileName: str = vFilePrefix + "_" + vInputName.decode("utf-8").strip() + "_" + funcDateString() + ".tar"
  vSetTarFileFullPath: str = os.path.join(vBckDir, vSetTarFileName)
  # Fill global array for usage later if vSendToSftp set to yes.
  if vSendToSftp.lower() == "yes":
    vGlobNameList.append(vSetTarFileName)
  # Execute export of volumes.
  vCmd: str = (vExportCmd + " " + vSetTarFileFullPath + " " + vInputName.decode("utf-8").strip())
  _ = subprocess.run(vCmd, shell=True, check=True)
  # Return info.
  return None

## Define function - Connect to SFTP.
def funcSftpConnect() -> None:
  try:
    # Initalize variables.
    global vScpClient
    vScpClient = paramiko.SSHClient()
    vScpClient.load_system_host_keys()
    vSetTimeout: int = int(vSftpTimeout)
    # Check if to ask for username & password or to use keyfile.
    if vSftpUseKey.lower() == "no":
      print('Entering Username & Password for remote server...')
      if vSetTimeout == 0:
        vScpClient.connect(vSftpHost, port=vSftpPortInt, username=vSftpUser, password=vSftpPass, timeout=None)
      else:
        vScpClient.connect(vSftpHost, port=vSftpPortInt, username=vSftpUser, password=vSftpPass, timeout=vSetTimeout)
    elif vSftpUseKey.lower() == "yes":
      # Get KeyFile.
      vKeyFile = paramiko.PKey.from_path(vSftpKeyFile)
      # Check if username is entered, if yes combine with key file, else use only key file.
      if vSftpUser != "":
        print('Using Username & KeyFile to connect to remote server...')
        if vSetTimeout == 0:
          vScpClient.connect(vSftpHost, port=vSftpPortInt, username=vSftpUser, pkey=vKeyFile, look_for_keys=False, timeout=None)
        else:
          vScpClient.connect(vSftpHost, port=vSftpPortInt, username=vSftpUser, pkey=vKeyFile, look_for_keys=False, timeout=vSetTimeout)
      else:
        print('Using KeyFile to connect to remote server...')
        if vSetTimeout == 0:
          vScpClient.connect(vSftpHost, port=vSftpPortInt, pkey=vKeyFile, look_for_keys=False, timeout=None)
        else:
          vScpClient.connect(vSftpHost, port=vSftpPortInt, pkey=vKeyFile, look_for_keys=False, timeout=vSetTimeout)
    # Open connection
    global vScpConn
    vScpConn = vScpClient.open_sftp()
    print('Connected to SFTP...')
  except Exception as vErr:
    # Send info to console and exit.
    print('Cannot connect to remote server, exiting...')
    print(vErr)
    exit(1)

## Define function - Send to SFTP.
def funcSendToSftp() -> None:
  try:
    # Open SFTP connection.
    funcSftpConnect()
    # Send info to console.
    print("Sending files to SFTP server...")
    # Iterate through file name list and send files.
    for vFile in vGlobNameList:
      # Send info to console.
      print("Uploading:", vFile)
      # Change directory on server.
      vScpConn.chdir(vSftpDir)
      # Build local path
      vSetFileFullPath: str = os.path.join(vBckDir, vFile)
      # Send file to server.
      _ = vScpConn.put(vSetFileFullPath, vFile)
      # Send info to console.
      print("Uploaded: ", vFile)
    # Send info to console.
    print("Done sending files to SFTP server...")
    # Close SFTP connection.
    funcSftpClose()
  except Exception as vErr:
    print('Could not send file...')
    # Close SFTP Connection.
    funcSftpClose()
    # Send info to console and exit.
    print(vErr)
    exit(1)

## Define function - Close SFTP connection.
def funcSftpClose() -> None:
  try:
    # Close active session if any.
    print("Closing remote session...")
    vScpConn.close()
    print("Remote session closed...")
  except Exception as vErr:
    # Send info to console and exit.
    print(vErr)
    exit(1)

## Define history function.
def funcKeepBackup(vGetDays: int, vGetDir: str) -> None:
  try:
    # Check if to keep a history or not.
    vIntDays: int = int(vGetDays)
    if vKeepBackup.casefold() == "yes":
      # Send info to console.
      print("Pruning backup folder, keeping", vIntDays, "days...")
      # Set today as current day.
      vTimeNow: int = int(time())
      # Remove files based on days to keep.
      for fname in os.listdir(vGetDir):
        if fname.startswith(vFilePrefix):
          if os.path.getmtime(os.path.join(vGetDir, fname)) < vTimeNow - vIntDays * 86400:
            os.remove(os.path.join(vGetDir, fname))
      # Send info to console.
      print("Done pruning backup folder...")
    elif vKeepBackup.casefold() == "no":
      # Send info to console.
      print("Removing all local backup files...")
      # Build file list and remove files.
      vSetFilePattern: str = os.path.join(vFilePrefix + "_")
      for fname in os.listdir(vGetDir):
        if fname.startswith(vSetFilePattern):
          os.remove(os.path.join(vGetDir, fname))
      # Send info to console.
      print("Done removing all local backup files...")
  except:
    # Send info to console.
    print("Could not clean backup folder...")

### Do the work ###

### Function - Main
def funcMain() -> None:
  ## Call the pre OS command function and run only if vPreBckCmd is set to yes.
  funcExecutePreOsCmd(vPreOsCmd)

  ## Call the volume export function.
  funcExportVolumes()

  ## Call the Sftp function and upload files only if vSendToSftp is set to yes.
  if vSendToSftp.lower() == "yes":
    funcSendToSftp()

  ## Call the post OS command function and run only if vPostBckCmd is set to yes.
  funcExecutePostOsCmd(vPostOsCmd)

  ## Call the history function to enable automatic housekeeping in the backup folder.
  funcKeepBackup(vKeepDaysInt, vBckDir)

## Execute funcMain to Run the whole shebang....
if __name__ == '__main__':
    funcMain()

#!/usr/bin/python3

#################################################################
# podman volume backup script written in python.                #
#                                                               #
# Author: Marcus Uddenhed                                       #
# Version: 1.2.1                                                #
# Date: 2024-05-01                                              #
# Requirements:                                                 #
# pysftp for SFTP functions, only if vSendToSftp is set to yes. #
#                                                               #
#################################################################

## Global variables.
vBckDir: str = ""                      # Backup folder to use during creation of volume exports and to store files locally.
vFilePrefix: str = ""                  # Name prefix of files, _date and .tar is added at the end, ex. 'prefix_volumename_date.tar'.
vKeepBackup: str = "no"                # Keep local backup files after sent to SFTP server, if no than nothing is kept locally.(no/yes)
vKeepDays: int = "20"                  # Number of days to keep local files before pruning the backup directory, relies on vKeepBackup.
vSendToSftp: str = "no"                # Should we send the files to a Sftp server.(no/yes)
vSftpUser: str = ""                    # User for the remote server, used both with password or key file.
vSftpPass: str = ""                    # Password for the remote server.
vSftpUseKey: str = "no"                # Use key file as authenticator against remote server for SFTP.
vSftpKeyFile: str = ""                 # Full path and key to use when connecting via key file instead of username/password.
vSftpDir: str = ""                     # Destination folder on remote server.
vSftpHost: str = ""                    # Remote server address.
vSftpPort: int = "22"                  # Remote server port.
vPreBckCmd: str = "no"                 # Run extra OS specific commands before backup.(no/yes)
vPostBckCmd: str = "no"                # Run extra OS specific commands after backup.(no/yes)

# External OS commands to execute before continuing with the rest of the script.
vPreOsCmd: list = [""]

# External OS commands to execute at the end of the script.
vPostOsCmd: list = [""]

# If you want to exclude or include volumes in backup you can use these two options.
# If both are empty it will do a backup of every volumes that exists.
# The include takes precedence over exclude pattern, so if you add to both the exclude
# lookup will be ignored, the words are CASE sensitive so "data" is not equal to "Data" and so on.
vIncludePattern: list = [""]
vExcludePattern: list = [""]

#### Do not edit anything below this line ####

## Module imports.
from datetime import datetime
from time import time
import subprocess
import os

# Volume list command
vListCmd: str = "podman volume list --format {{.Name}}"

# Volume export command
vExportCmd: str = "podman volume export --output"

#### Script Action

## Import pysftp only if vSendToSftp set to yes.
if vSendToSftp.lower() == "yes":
  import pysftp

## Define global array for volume file names.
vGlobNameList: list = []

## Get current date
def funcDateString() -> datetime:
  # Returns the today string year, month, day.
  return datetime.now().strftime("%Y%m%d")

## Define function for Pre OS commands.
def funcExecutePreOsCmd(vPreOsCmd: list) -> None:
  try:
    if vPreBckCmd.casefold() == "yes":
      # iterate through each specified command.
      for vExecute in vPreOsCmd:
        subprocess.run(vExecute, shell=True, check=True)
      # Send info to console.
      print("OS commands has been executed...")
  except:
    # Send info to console.
    print("Could not execute OS command...")

## Define function for Pre OS commands.
def funcExecutePostOsCmd(vPostOsCmd: list) -> None:
  try:
    if vPostBckCmd.casefold() == "yes":
      # iterate through each specified command.
      for vExecute in vPostOsCmd:
        subprocess.run(vExecute, shell=True, check=True)
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
    vGetList: list = subprocess.Popen(vListCmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Create an array with the names.
    vNameList: list = vGetList.stdout.readlines()
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
        funcDoBackup(vName)
        print("Volume exported: ", vName.decode("utf-8").strip())
  except:
    # Send info to console.
    print("Could not export one or more volumes...")

## Define backup function
def funcDoBackup(vInputName) -> None:
  # Build filename.
  vSetTarFile: str = os.path.join(vBckDir, vFilePrefix + "_" + vInputName.decode("utf-8").strip() + "_" + funcDateString() + ".tar")
  # Fill global array for usage later if vSendToSftp set to yes.
  if vSendToSftp.lower() == "yes":
    vGlobNameList.append(vSetTarFile)
  # Execute export af volumes.
  vCmd: str = (vExportCmd + " " + vSetTarFile + " " + vInputName.decode("utf-8").strip())
  subprocess.run(vCmd, shell=True, check=True)
  # Return info.
  return None

## Define function send to SFTP.
def funcSendToSftp(vFolder: str) -> None:
  try:
    if vSendToSftp.casefold() == "yes":
      # int literal to int...
      vPort: int = int(vSftpPort)
      # Send info to console.
      print("Sending files to SFTP server...")
      # Iterate through file name list and send files.
      for vFile in vGlobNameList:
        # Send info to console.
        print("Uploading:", vFile)
        # Check connection parameters and build connection string.
        if vSftpUseKey.lower() == "yes":
          # Connect to SFTP with key fil and upload file.
          with pysftp.Connection(host=vSftpHost, port=vPort, username=vSftpUser, private_key=vSftpKeyFile) as sftp:
            # Change directory.
              with sftp.cd(vFolder):
                # Upload file
                sftp.put(vFile)
        elif vSftpUseKey.lower() == "no":
          # Connect to SFTP with username/password and upload file.
          with pysftp.Connection(host=vSftpHost, port=vPort, username=vSftpUser, password=vSftpPass) as sftp:
            # Change directory.
            with sftp.cd(vFolder):
              # Upload file
              sftp.put(vFile)
        # Send info to console.
        print("Uploaded: ", vFile)
      # Send info to console.
      print("Done sending files to SFTP server...")
  except:
    # Send info to console.
    print("Could not connect to server or upload file...")

## Define history function.
def funcKeepBackup(vGetDays: int, vGetDir: str) -> None:
  try:
    # Check if to keep a history or not.
    vIntDays: int = int(vGetDays)
    if vKeepBackup.casefold() == "yes":
      # Send info to console.
      print("Pruning backup folder, keeping", vIntDays, "days...")
      # Set today as current day.
      vTimeNow: int = time()
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
  funcSendToSftp(vSftpDir)

  ## Call the post OS command function and run only if vPostBckCmd is set to yes.
  funcExecutePostOsCmd(vPostOsCmd)

  ## Call the history function to enable automatic housekeeping in the backup folder.
  funcKeepBackup(vKeepDays, vBckDir)

## Execute funcMain to Run the whole shebang....
if __name__ == '__main__':
    funcMain()
#!/usr/bin/python3

#################################################################
# podman volume backup script written in python.                #
#                                                               #
# Author: Marcus Uddenhed                                       #
# Revision: 1.1.0                                               #
# Revision Date: 2024-03-25                                     #
# Requirements:                                                 #
# pysftp for SFTP functions, only if vSendToSftp is set to yes. #
#                                                               #
#################################################################

## Module imports.
from datetime import datetime
from time import time
import subprocess
import os

## Global variables.
vBckDir=""                      # Backup folder to use during creation of volume exports and to store files locally.
vFilePrefix=""                  # Name prefix of files, _date and .tar is added at the end, ex. prefix_volumename_date.tar.
vKeepBackup="no"                # Keep local backup files after sent to SFTP server, if no than nothing is kept locally.(no/yes)
vKeepDays="20"                  # Number of days to keep local files before pruning the backup directory, relies on vKeepBackup.
vSendToSftp="no"                # Should we send the files to a Sftp server.(no/yes)
vSftpUser=""                    # User for the remote server, used both with password or key file.
vSftpPass=""                    # Password for the remote server.
vSftpUseKey="no"                # Use key file as authenticator against remote server for SFTP.
vSftpKeyFile=""                 # Full path and key to use when connecting via key file instead of username/password.
vSftpDir=""                     # Destination folder on remote server.
vSftpHost=""                    # Remote server adress.
vSftpPort="22"                  # Remote server port.
vPreBckCmd="no"                 # Run extra OS specific commands before backup.(no/yes)
vPostBckCmd="no"                # Run extra OS specific commands after backup.(no/yes)

# External OS commands to execute before continuing with the rest of the script.
vPreOsCmd=[""]

# External OS commands to execute at the end of the script.
vPostOsCmd=[""]

# Volume list command
vListCmd="podman volume list --format {{.Name}}"

# Volume export command
vExportCmd="podman volume export --output"

#### Script Action

## Import pysftp only if vSendToSftp set to yes.
if vSendToSftp == "yes":
    import pysftp

## Define global array for volume file names.
gNameArray = []

## Get current date
def funcDateString():
    # Returns the today string year, month, day.
    return datetime.now().strftime("%Y%m%d")

## Define function for Pre OS commands.
def funcExecutePreOsCmd(vPreOsCmd):
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
def funcExecutePostOsCmd(vPostOsCmd):
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
def funcExportVolumes():
    try:
        # Mark gNameArray global
        global gNameArray
        # Get volume names.
        vGetList = subprocess.Popen(vListCmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Create an array with the names.
        vNameArray = vGetList.stdout.readlines()
        # iterate through each specified volume name.
        for vName in vNameArray:
            vSetTarFile=os.path.join(vBckDir, vFilePrefix + "_" + vName.decode("utf-8").strip() + "_" + funcDateString() + ".tar")
            # Fill global array.
            gNameArray.append(vSetTarFile)
            # Execute export af volumes.
            vCmd=(vExportCmd + " " + vSetTarFile + " " + vName.decode("utf-8").strip())
            subprocess.run(vCmd, shell=True, check=True)
            # Send info to console.
            print("Volume exported: ", vName.decode("utf-8").strip())
    except:
        # Send info to console
        print("Could not export one or more volumes...")

## Define function send to SFTP.
def funcSendToSftp(vFolder):
    try:
        if vSendToSftp.casefold() == "yes":
            # Send info to console.
            print("Sending files to SFTP server...")
            # Convert port to integer, needed since we use "" above to keep it a bit more tidy.
            vIntPort=int(vSftpPort)
            # Iterate through file name array and send files.
            for vFile in gNameArray:
                # Check connection parameters and build connection string.
                if vSftpUseKey.lower() == "yes":
                    # Connect to SFTP with key fil and upload file.
                    with pysftp.Connection(host=vSftpHost, port=vIntPort, username=vSftpUser, private_key=vSftpKeyFile) as sftp:
                        # Change directory.
                        with sftp.cd(vFolder):
                            # Upload file
                            sftp.put(vFile)
                elif vSftpUseKey.lower() == "no":
                    # Connect to SFTP with username/password and upload file.
                    with pysftp.Connection(host=vSftpHost, port=vIntPort, username=vSftpUser, password=vSftpPass) as sftp:
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
def funcKeepBackup(vGetDays, vGetDir):
    try:
        # Check if to keep a history or not.
        vIntDays=int(vGetDays)
        if vKeepBackup.casefold() == "yes":
            # Send info to console.
            print("Pruning backup folder, keeping", vIntDays, "days...")
            # Set today as current day.
            vTimeNow=time()
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
            vSetFilePattern=os.path.join(vFilePrefix + "_")
            for fname in os.listdir(vGetDir):
                if fname.startswith(vSetFilePattern):
                    os.remove(os.path.join(vGetDir, fname))
            # Send info to console.
            print("Done removing all local backup files...")
    except:
        # Send info to console.
        print("Could not clean backup folder...")

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
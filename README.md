# oVolumeBackup

Python script for exporting and sending podman containers volumes to remote backup storage via SFTP.

#### Functionality

- Export volume data to a `tar` file.
- Send to `SFTP` for remote storage.
- Can utilize `SSH` keys for SFTP connection.
- Include/exclude volumes from backup.
- Keep certain backup versions locally.

#### Installation

Download the latest version into a suitable folder on your system and then to get the script running you need to do some configuration in your system as well in the script.

##### System

The script needs a Python `venv` for best compatibility.

On Debian / Ubuntu the package needed is called `python3.xx-venv` and must be installed before continuing, for other systems adjust needed package and the commands below so that they work for you system.

Install package, replace `xx` with the version you want to install.

```bash
sudo apt install python3.xx-venv
```

##### Virtual Environment

The `venv` should always be created in the home folder of the user running the script.

When you are logged in to the user that should run the script change directory to the home folder.

Must be the same user that runs the containers or it will not work.

```bash
cd ~/
```

Then run the following command, this will create a virtual environment just for this script.

```bash
python3 -m venv .venv/oVolumeBackup
```
When the `venv` is created, if you plan to send the backup to a `SFTP` server, the `paramiko` Python package is needed.

To install it do the following.

```bash
source .venv/oVolumeBackup/bin/activate
pip3 install wheel
pip3 install paramiko
deactivate
```
Now the Python virtual environment is ready for use.

##### Script

The script needs som configuration so that it can do the work, each option to configure is explained within the script.

The top row in the script should point to your `venv` that you created before, for example if run as root it should look something like this, replace path to the correct `user` home directory.

```bash
#!/home/user/.venv/oVolumeBackup/bin/python3
```

To run the script as an executable change the permission like this, make sure only the user running the script has permissions on it if you use plain username & password for the `SFTP` server.

```bash
chmod 770 path/to/the/script/oVolumeBackup.py
```

#### Usage

The script can be called manually when needed or scheduled to run on a recurring pattern.

#### Security

The main security consideration is how the permissions is set on the script and usage of plain text `username`/`password` or not.

Always try to set as permissive as possible and use SSH keys if possible.

#### More

My homepage: [Link](https://www.osource.se)

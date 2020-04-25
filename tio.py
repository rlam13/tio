#!/usr/local/bin/python3
#
# Richard Lam, April 2020
#
# Simple and limited CLI interface to Tenable.IO.
# 
# Features:
# 1) show scan configuration and history of each configured scan.
# 2) export specific scan to local disk in csv/pdf/html/nessus. 
#    Note: PDF & HTML option only available within 90 days of the scan.
# 3) show server information.
# 4) lay groundwork to extend capability of this CLI to Tenabloe.io (PyTenable API).
#
# Requirements to run this script:
#
# 1) Linux or Unix based OS.  (Could be ported to Windows, presently it will not work)
# 2) Python 3
# 3) PyTenable Python module
#    Install by using:
#    pip3 install pytenable
#
# References:
# https://pytenable.readthedocs.io/en/stable/
# https://github.com/tenable/pyTenable
#
#
# Script automatically checks for presence of API keys at ~/.tio/client.json.
# If API keys are not present, then user is prompted for key on first use and saved.
# NOTE: It is up to you to secure your API keys!! In this form it is stored unencrypted
#       on your local drive.  You have been warned.
#
#
# Examples:
# python3 tio.py info
# 
# python3 tio.py export -s 1337 -hid 12345678 <name_of_file> pdf html nessus csv
#
# python3 tio.py server


from tenable.io import TenableIO
import json
import datetime
import argparse
import os
import sys


# default function for info subcommand.  Displays information of configured scans for tenable.io
def configured_scans_info (tio, args):

    # Retrieve list of configured scans and print
    configured_scans = []

    print ()
    print ('STATUS\t\tSCAN_ID/UUID\t\t\t\t- SCAN NAME')
    for scan in tio.scans.list():
        print ('{status}\t{id}/{uuid} - {name}'.format(**scan))
        configured_scans.append (scan)

    num_configured_scans = len (configured_scans)
    print ("Number of scans configured: " + str(num_configured_scans))
    print ()
        
    scan_id = args.scan_id
    offset = args.offset
    uuid = args.uuid

    if scan_id:
        get_scan_history (tio, scan_id, offset, configured_scans)

    if scan_id and uuid:
        show_scan_info (tio, scan_id, uuid, configured_scans)


# Show scan information for a configured scan
def show_scan_info (tio, scan_id, uuid, scan_num_name):

    for field, value in tio.scans.info(scan_id, uuid).items():
        print (field,":", value)
    print ()
        
    
# Show scan results for an executed scan
def get_scan_history(tio, scan_id, offset, configured_scans):

    num_configured_scans = len (configured_scans)
    
    # Skip looking up if the requested configured scan has no records
    for i in range (num_configured_scans):
       if json.dumps (configured_scans[i]["id"]) == str(scan_id):
           if json.dumps (configured_scans[i]["creation_date"]) == "0":
               print ()
               print ("The scan_id referenced has zero records.")
               print ()
               return

    # Retreive history of completed scans by scan_id
    scan_info = []
    
    for history in tio.scans.history(scan_id):
        scan_history = json.dumps(history)
        scan_info.append(history)

    num_scan_info = len (scan_info)
        
    print ()
    print ()
    print ('SCAN_ID\t\tSCAN NAME')

    for i in range(num_configured_scans):
        if json.dumps (configured_scans[i]["id"]) == str(scan_id):
            print (json.dumps (configured_scans[i]["id"]) + "\t\t" + json.dumps (configured_scans[i]["name"])) 
            break

    print ()

    if offset > num_scan_info:
        offset = num_scan_info
        print ("Note: maximum records for this configured scan is: ", str (offset))
        print ()

    for i in range(offset):
        print ("Date & Time scan started: ", datetime.datetime.fromtimestamp (int (json.dumps (scan_info[i]['time_start']) ) ))
        print ("Date & Time scan ended:   ", datetime.datetime.fromtimestamp (int (json.dumps (scan_info[i]['time_end']) ) ))
        print (json.dumps (scan_info[i], sort_keys=True, indent=0))
        print ()


# Export scan to filename and format provided.
# Note, scans results greater than 90 days or older, can only be exported as CSV or Nessus (xml) format.
def export_scans (tio, args):

    scan_id = args.scan_id
    hid = args.history_id
    filename = args.filename.name
    file_format = args.file_format

    # Iterate through list to export all formats
    print ()
    print ("Exporting the follow files to current directory:")
    print ()

    for file_type in file_format:
        with open (filename + '.' + file_type, "wb") as file_export:
            tio.scans.export(scan_id, history_id=hid, format=file_type, fobj=file_export)
        print (filename + '.' + file_type)

    # remove blank file generated by above command - hokey band-aid fix until proper solution is determined
    os.remove(filename)
    print ()


# Show properties and current status of server.
def server_info (tio, arg):

    server_properties = tio.server.properties()
    #print (server_properties)
    print ()
    print ("SERVER PROPERTIES: \n" + json.dumps (server_properties, indent=2))
    server_status = tio.server.status()
    print ()
    print ()
    print ("SERVER STATUS: \n" + str(server_status))
    print ()


# Check for configuration file for API keys.
# If API keys are not stored, prompt user and store them.
def check_api_keys():

    #tio = TenableIO('TIO_ACCESS_KEY', 'TIO_SECRET_KEY')

    home = os.path.expanduser ('~')

    try:
        with open (home + "/.tio/client.json", "r") as clientfile:
            apikeys = json.load (clientfile)
            tio_access_key = apikeys['tenable_io']['a_key']
            tio_secret_key = apikeys['tenable_io']['s_key']
            tio = TenableIO(tio_access_key, tio_secret_key)
            return tio
    except IOError:
        keys = { "tenable_io": {"a_key": "", "s_key": "" } }
        print ()
        print ("WARNING: User API file '~/.tio/client.json' not found.")
        print ()
        print ("Tenable.io access keys and secret keys are required for all endpoints.")
        print ("Please input Access and Secret key")
        print ("Reference: https://developer.tenable.com/")
        print ()
        tio_access_key = input ("Enter Tenable.io'AccessKey': ")
        tio_secret_key = input ("Enter Tenable.io'SecretKey': ")
        keys ["tenable_io"]["a_key"] = tio_access_key
        keys ["tenable_io"]["s_key"] = tio_secret_key

        if not os.path.exists (home + "/.tio"):
            os.mkdir (home + "/.tio", 0o700)
        with open (home + "/.tio/client.json", "w") as storekeyfile:
            json.dump (keys, storekeyfile, ensure_ascii=False,sort_keys=True, indent=2)
        os.chmod (home + "/.tio/client.json", 0o600)

        tio = TenableIO(tio_access_key, tio_secret_key)

        return tio
    

def main():

    parser = argparse.ArgumentParser (add_help=True,
             description="CLI interface for TenableIO \n\nView help page for each command for detailed information\n\n" +
             "python3 tio.py info -h\n\npython3 tio.py export -h\n\npython3 tio.py server -h",
             formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers (help='commands', dest='subparser')

    info_parser = subparsers.add_parser ('info', description="Display information for all configured scans\n\n")

    info_parser.add_argument('-s', '--scan_id', type=int, help="show latest scan(s) by scan_id number ")
    info_parser.add_argument('-o', '--offset', type=int, default=1, help="indicate number of scans to display (starting with most recent scan first)")
    info_parser.add_argument('-u', '--uuid', type=str, help="include uuid with scan_id to view scan configuration")
    info_parser.set_defaults (func=configured_scans_info)

    export_parser = subparsers.add_parser ('export', help="Export scan report", description="Eg. python3 tio.py export -s 1337 -u xxxxxxxx <yourfilename> pdf")
    export_parser.add_argument('-s', '--scan_id', type=int, help="indicate scan_id to export")
    export_parser.add_argument('-hid', '--history_id', type=int, help="history_id of scan to export. (obatain from \"id\" field, from info -s xx command)")
    export_parser.add_argument ('filename', type=argparse.FileType('w'), help='filename to save to', metavar="filename")
    export_parser.add_argument ('file_format', type=str, default='csv', choices=['nessus', 'html', 'pdf', 'csv'], nargs='+', help='csv pdf html nessus(xml)', metavar="file_format")
    export_parser.set_defaults (func=export_scans)

    server_parser = subparsers.add_parser ('server', help="Server information")
    server_parser.set_defaults (func=server_info)
    
    args = parser.parse_args()

    # If there are no arguments to pass, aside from --help (-h) then display help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()

    try:
        tio = check_api_keys()
        args.func(tio,args)
    except AttributeError:
        parser.print_help()
        parser.exit()
    
if __name__ == "__main__":
    main()
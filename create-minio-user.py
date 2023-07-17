#!/usr/bin/env python3

import minio
import os
import io
import string
import random
import requests
import urllib3
import subprocess

# Set the MinIO endpoint
MINIO_ENDPOINT = "172.17.0.1:9000"

def attach_minio_policy(username, policy_name, root_username, root_password):
   # will have to use subprocess commands for this ...
    # Configure the MinIO host connection
    command_configure = ["mc", "config", "host", "add", "myminio", f"http://{MINIO_ENDPOINT}", root_username, root_password]
    subprocess.run(command_configure, check=True)

    # Create a new user
    command_attach_policy = ["mc", "admin", "policy", "attach", "--user", username, "myminio", policy_name]
    subprocess.run(command_attach_policy, check=True)
    print(f"Policy '{policy_name}' attached to user '{username}' successfully.")


def create_minio_policy(policy_name, policy_content, root_username, root_password):
    """
    Creates a new policy on the MinIO server.

    policy_name: string. The name of the new policy.
    policy_content: string. The content of the new policy.
    root_username: string. The username of the root user.
    root_password: string. The password of the root user.
    """

    # Save the policy to a temporary file
    policy_file = "/tmp/minio_policy.json"
    with open(policy_file, "w") as f:
        f.write(policy_content)

    # Configure the MinIO host connection
    command_configure = ["mc", "config", "host", "add", "myminio", f"http://{MINIO_ENDPOINT}", root_username, root_password]
    subprocess.run(command_configure, check=True)

    # Run the mc command to set the policy
    command = [ "mc", "admin", "policy", "create", "myminio", policy_name , policy_file ]
    subprocess.run(command, check=True)

    # Cleanup: Remove the temporary policy file
    subprocess.run(["rm", policy_file])

    print(f"Policy '{policy_name}' created successfully.")

def create_minio_user(username, password, root_username, root_password):
    # Configure the MinIO host connection
    command_configure = ["mc", "config", "host", "add", "myminio", f"http://{MINIO_ENDPOINT}", root_username, root_password]
    subprocess.run(command_configure, check=True)

    # Create a new user
    command_create_user = ["mc", "admin", "user", "add", "myminio", username, password]
    subprocess.run(command_create_user, check=True)
    print(f"User '{username}' with password '{password}' created successfully.")

def get_password(user_name):
    """
    asks the user to enter a password or to use a randomly generated password
    returns: string. the password to be used for the user
    """
    password = None

    answer = ""
    while answer != "y" and answer != "n":
        if answer == "exit":
            exit()
        print(f"Do you want to use a randomly generated password username={user_name} (y/n/exit)") # noqa
        answer = input()
    if answer == "y":
        password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(8)) # noqa
        print(f"password={password}")

    while answer != "y":
        if answer == "exit":
            exit()
        print(f"Please enter the password to be used for the username={user_name}:") # noqa
        password = input()
        # check if the password is at least 8 characters long
        # if not repeat the question
        while len(password) < 8:
            print("The password must be at least 8 characters long.")
            print(f"Please enter the password to be used for username={user_name}:") # noqa
            password = input()
        print(f"password={password}")
        print("Is this correct? (y/n/exit)")
        answer = input()

    return password

def get_country_and_center_id():
    """
    Asks the user for the 3-letter ISO country-code
    and a string identifying the center hosting the wis2box.

    returns: tuple. (country_code, center_id)
    """
    answer = ""
    while answer != "y":
        if answer == "exit":
            exit()
        print("Please enter the 3-letter ISO country-code for the user:")
        country_code = input()
        # check that the input is a 3-letter string
        # if not repeat the question
        while len(country_code) != 3:
            print("The country-code must be a 3-letter string.")
            print("Please enter your 3-letter ISO country-code:")
            country_code = input()
        # make sure the country-code is lowercase
        country_code = country_code.lower()
        print("Please enter the centre-id for the user")
        center_id = str(input()).lower()
        # check that the input is valid
        # if not repeat the question
        while any(char in center_id for char in '.# +') or len(center_id) < 8: # noqa
            print("The centre-id can not contain spaces, the '+' or '#' or '.' character and must be at least 8 characters long.") # noqa
            print("Please enter the string identifying the center hosting the wis2box:") # noqa
            center_id = str(input()).lower()
        # ask the user to confirm their choice and give them the option to change it # noqa
        # and give them the option to exit the script
        print("The country-code will be set to:")
        print(f"  {country_code}")
        print("The centre-id will be set to:")
        print(f"  {center_id}")
        print("Is this correct? (y/n/exit)")
        answer = input()

    return (country_code, center_id)

def test_new_user(minio_path, username, password):
    """
    tests if the new user can write to the minio bucket
    
    minio_path: string. the path to the minio bucket
    username: string. the username of the new user
    password: string. the password of the new user
    """
    
    # define content
    content = 'placeholder for directory'
    # Convert content to bytes
    content_bytes = content.encode('utf-8')
    # Create a file-like object from the content
    content_file = io.BytesIO(content_bytes)

    try:
        # create minio client
        client = minio.Minio(
            MINIO_ENDPOINT,
            access_key=username,
            secret_key=password,
            secure=False
        )
        # put the file in the minio bucket
        client.put_object(
            'wis2box-incoming',
            minio_path + '/placeholder.md',
            data=content_file,
            length=len(content_bytes)
        )
        print(f"created {minio_path}/placeholder.md in wis2box-incoming for user {username}") # noqa
    except minio.InvalidResponseError as err:
        print(f"Error creating {minio_path}/placeholder.md in wis2box-incoming: {err} for user {username}") # noqa

def main():
    """
    main function

    creates minio users and policies
    """

    # get environment variables for WIS2BOX_STORAGE_USERNAME and WIS2BOX_STORAGE_PASSWORD
    root_username = os.getenv('WIS2BOX_STORAGE_USERNAME')
    root_password = os.getenv('WIS2BOX_STORAGE_PASSWORD')

    # get the country-code and center-id from the user
    country_code, center_id = get_country_and_center_id()
    username = f'{country_code}.{center_id}_observer'
    password = get_password(username)

    # create a minio user
    create_minio_user(username, password, root_username, root_password)
    # create a minio path to be used in the policy
    minio_path = f'{country_code}/{center_id}/data/core/weather/surface-based-observations/synop'
    policy_name = f"{username}-policy"
    policy_content = """
    {
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": ["s3:ListAllMyBuckets", "s3:GetBucketLocation"],
        "Effect": "Allow",
        "Resource": ["arn:aws:s3:::*"]
        },
        {
        "Action": ["s3:GetObject"],
        "Effect": "Allow",
        "Resource": ["arn:aws:s3:::*"]
        },
        {
        "Action": ["s3:PutObject"],
        "Effect": "Allow",
        "Resource": ["arn:aws:s3:::wis2box-incoming/MINIO_PATH*"]
        }
    ]
    }
    """.replace('MINIO_PATH', minio_path)
    # create a minio policy
    create_minio_policy(policy_name, policy_content, root_username, root_password) # noqa
    # attach the policy to the user
    attach_minio_policy(username, policy_name, root_username, root_password)

    test_new_user(minio_path, username, password)
    print("Done!")

if __name__ == "__main__":
    main()
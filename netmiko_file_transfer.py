"""
Didn't verify memory size matches 256M (programmatically)
Didn't verify flash size matches 128M (programmatically)
Hard-coded 'flash:'
"""
import sys
import re
# import getpass

from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_file_transfer
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.tasks.networking import netmiko_send_config

from nornir_utilities import nornir_set_creds, std_print


def os_upgrade(task):
    file_name = task.host.get('img')
    task.run(
        task=netmiko_file_transfer,
        source_file=file_name,
        dest_file=file_name,
        direction='put',
    )
    print("Just ran OS_upgrade function")

    return ''


def set_boot_var(task):
    """
    Set the boot variable for Cisco IOS.
    return True if boot variable set
    return False if staging verification steps failed (i.e. before the boot variable was set).
    """
    primary_img = task.host.get('img')
    backup_img = task.host.get('backup_img')

    # Check images are on the device
    ### CHANGED TO ONLY DO PRIMARY IMAGE IN COMMAND STRING
    for img in (primary_img, backup_img): #, backup_img  ### removed backup_img
    	# had to take into account the fact that the current running image is installed
    	# in a subdirectory
        # file_only = img.split('/')
        # if len(file_only) == 1:
        # 	continue
        # else:
        # 	file_only = file_only[1]
        result = task.run(
            netmiko_send_command,
            command_string=f"dir flash:/{img}"
        )
        ## DEBUG ##
        # print(f"This is result[0] after checking flash", result[0])
        
        ## DEBUG ##
        print(f"This is result:", result)
        print("\n")       
        print(f"This is result[0]:", result[0])
        print("\n")
        print(f"This is result[0].result:", result[0].result)
        print("\n")

        output = result[0].result
        

        

        # Drop the first line as that line always contains the filename
        output = re.split(r"Directory of.*", output, flags=re.M)[1]
        # if file_only not in output:
        if img not in output:
            print("The image was not found on the device directory.")
            return False

        ## DEBUG ##
        print(f"This is output for", img, " after regex", output)
        print("\n")


    commands = f"""
default boot system
boot system flash:{primary_img};flash:{backup_img}
"""

## removed from commadns and replaced with above single statement
# boot system flash {primary_img}
# boot system flash {backup_img}



    command_list = commands.strip().splitlines()
    output = task.run(
        netmiko_send_config,
        config_commands=command_list
    )
    
    ## DEBUG ##
    print(f"This is the command list", command_list)
    print("\n")
    print(f"This is output from send config", output)
    print("\n")
    return True


# def set_boot_var(task):
#     """
#     Set the boot variable for Cisco IOS.
#     return True if boot variable set
#     return False if staging verification steps failed (i.e. before the boot variable was set).
#     """
#     primary_img = task.host.get('img')
#     backup_img = task.host.get('backup_img')

#     # Check images are on the device

#     result = task.run(
#         netmiko_send_command,
#         command_string=f"dir flash:/{primary_img}"
#     )
#     ## DEBUG ##
#     # print(f"This is result[0] after checking flash", result[0])
    
#     ## DEBUG ##
#     print(f"This is result:", result)
#     print("\n")       
#     print(f"This is result[0]:", result[0])
#     print("\n")
#     print(f"This is result[0].result:", result[0].result)
#     print("\n")

#     output = result[0].result
    

#         # Drop the first line as that line always contains the filename
#     output = re.split(r"Directory of.*", output, flags=re.M)[1]
#     # if file_only not in output:
#     if primary_img not in output:
#         print("The image was not found on the device directory.")
#         return False

#     ## DEBUG ##
#     print(f"This is output for", primary_img, " after regex", output)
#     print("\n")


#     commands = f"""
# default boot system
# boot system flash {primary_img}
# """
# ### REMOVED THIS FROM COMMANDS::::   boot system flash {backup_img}

#     command_list = commands.strip().splitlines()
#     output = task.run(
#         netmiko_send_config,
#         config_commands=command_list
#     )

# 	## DEBUG ##
#     print(f"This is the command list", command_list)
#     print("\n")
#     print(f"This is output from send config", output)
#     print("\n")
#     return True


def continue_func(msg="Do you want to continue (y/n)? "):
    response = input(msg).lower()
    if 'y' in response:
        return True
    else:
        sys.exit()


def main():

    # Initialize Nornir object using hosts.yaml and groups.yaml
    brg = InitNornir(config_file="nornir.yml")
    nornir_set_creds(brg)

#### COMMENTED OUT FOR TESTING WITHOUT SENDING FILES  #########
    # print("Transferring files")
    # result = brg.run(
    #    task=os_upgrade,
    #    num_workers=20,
    # )
    # # print(f"This is the result of OS_upgrade:",result)


    # Filter to only a single device
    # brg_ios = brg.filter(hostname="cisco2.twb-tech.com")  # this is original from Kirk Byer
    brg_ios = brg.filter(hostname="192.168.2.101")    
    

    aggr_result = brg_ios.run(task=set_boot_var)
    
      ## DEBUG ##
    # std_print(aggr_result)
    # print(f"the result after set_boot is:",aggr_result)
    # print("\n")
    # print(type(aggr_result))
    # print("\n")
    # print("aggr_result.items()",aggr_result.items())
    # print("\n")
    # print("aggr_result['switchVT'][0].result", aggr_result['switchVT'][0].result)
    # print("\n")
    # print("aggr_result[0][0].result", aggr_result[0][0].result)
    # print("\n")

    # If setting the boot variable failed (assumes single device at this point)
    for hostname, val in aggr_result.items():
        if val[0].result is False:
            sys.exit("Setting the boot variable failed")

    # Verify the boot variable
    result = brg_ios.run(
        netmiko_send_command,
        command_string="show run | section boot",
    )
    
    print(f"This is the section boot: ",result)
   
    continue_func()

    # Save the config
    result = brg_ios.run(
        netmiko_send_command,
        command_string="write mem",
    )
    
    print(f"Just wrote memory: ",result)


    # Reload
    continue_func(msg="Do you want to reload the device (y/n)? ")
    result = brg_ios.run(
        netmiko_send_command,
        use_timing=True,
        command_string="reload",
    )

    # Confirm the reload (if 'confirm' is in the output)
    for device_name, multi_result in result.items():
        if 'confirm' in multi_result[0].result:
            result = brg_ios.run(
                netmiko_send_command,
                use_timing=True,
                command_string="y",
            )

    print("Devices reloaded")


if __name__ == "__main__":
    main()
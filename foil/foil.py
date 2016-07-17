#!/usr/bin/python
""" The foil module is a thin wrapper around multiple backend databases that 
    provides basic connection management and config file control
        
    The foil module provides multiple wrapper objects. The goal of this module 
    is to serve as a standard library for multiple projects. 
    
    This module contains the following Classes that are meant for external use: 
    
    #. Config
    #. Mongo
    
    This module also contains the following module functions: 
    
    #. str_to_bool

"""


__author__ = "Barrett Edwards"
__maintainer__ = "Barrett Edwards"
__copyright__ = "Copyright 2016"
__license__ = "MIT"
__version__ = "0.1.0"
__email__ = "BarrettEdwardsOSS@gmail.com"
__status__ = "Development"


import os 
import argparse
import ConfigParser
import urllib2 
import json 
from datetime import datetime
import time


import pymongo
import sshtunnel


def str_to_bool(s):
    """ Convert multiple string sequence possibilities to a simple bool
    
    There are many strings that represent True or False connotation. For 
    example: Yes, yes, y, Y all imply a True statement. This function 
    compares the input string against a set of known strings to see if it 
    can be construed as True.
    
    True strings: TRUE, True, true, 1, Y, y, YES, Yes, yes
    
    Args:
        s (string): String to convert into a bool
    
    Returns:
        bool: Returns True if the input string is one of the known True strings
    
    """

    if s.strip() in ['TRUE', 'True', 'true', '1', 'Y', 'y', 'YES', 'Yes', 'yes']:
        return True 
    else:
        return False
            

class FoilError(Exception):
    """A Base class for all Foil Exceptions."""
    pass


class Config():
    """ Class to manage config file loading, saving, and access
    
    This class is used to manage the loading, saving, and accessing of an 
    application config file. The theory of operations is that the user 
    instances this class and provides a filename of a pre-existing config file 
    in the file system. The user calls load() to load the config file into 
    this object. The user then requests specific entries using the get() 
    method. 
    
    This Config object does not have a default configuration entries. The 
    user is expected to provide a pre-populated config file that can be loaded 
    using the load() method or the user can initialize the Config object with 
    a dict object using the init() command and then write it out using the 
    write() method. 
    
    Instancing this class does not automatically load the specified config 
    file. Even if the user calls Config() and provides a config_filename the 
    user still needs to explicitly call load() to load the config file. 
    
    Example Config File::
    
        [Section1]
        option1 = value1
        option2 = value2

        [Section2]
        option1 = value3
    
    Typical Load Example::
        
        config = Config(filename='.config')
        config.load()
        value = config.get(section_name,option_name)
    
    Initialization Example::
    
        new_config_dict = {}
        new_config_dict["Section"] = {}
        new_config_dict["Section"]["Option"] = "value"
        
        config = Config()
        config.init(new_config_dict)
        config.write(filename='.config')
    
    Args: 
    
        filename (str): File name location of config file to use. 
    
    """
        
    def __init__(   self,
                    filename='.config'):
                    
        # self.config is the dict holding the config entries 
        self.config = None    
        
        self.filename = filename
            
        return
    
    def get(self, section, option, casttype=None):
        """Get the specified value from the config file and cast it as a 
        specific variable type if requested.
        
        This is just a basic getter method. The config file is loaded into 
        memory as a dict object and this get method attempts to extract the 
        requested value but catches a KeyError if the requested value doesn't 
        exist.
        
        The config file stores all variables as strings. So the user must 
        explicitly cast the return value into a non string object. This 
        method can cast the return value as a few variable types if requested.
        
        Example::
        
            config = Config(filename='.config')
            config.load()
            value = config.get(section_name,option_name, casttype='bool')
        
        Args: 
        
            section (string): Section name of requested value
            
            option (string): Option name of requested value
            
            casttype (string): The variable type to cast the return value.
                               This can be 'bool' or 'int'                               
        
        """
        
        value=None
    
        try: 
            value = self.config[str(section)][str(option)]
        except KeyError as e: 
            print "Error: Could not obtain config entry: ", str(section) + ":" + str(option)
    
        # Cast the value as the requested type
        if casttype == 'bool':
            value = str_to_bool(value)
    
        if casttype == 'int':
            value = int(value)
    
        return value

    def load(self, filename=None):
        """Loads a config file into memory
        
        The config file is assumed to be a ini style configuration file. If 
        the user passes in a filename here, that filename will be loaded. If 
        the user omits the filename here, then the load will use the filename 
        provided when the Config class was created. 
        
        Example::
        
            config = Config()
            config.load(filename='.config')
            value = config.get(section_name,option_name, casttype='bool')
        
        Args: 
            filename (string): name of ini file to load. 
        
        Returns:
            bool: Returns True if load of config file was successful
            
        """
               
        # if user didn't pass in a filename use one provided when Config() was 
        # created
        if filename is None:
            filename = self.filename

        # if filename is None here, then the user didn't provide a filename 
        # here or when Config() was instanced so fail
        if filename is None:
            print "Error: Could not load config file as no filename was provided"
            return False
            
        # validate filename 
        filepath = os.path.expanduser(filename)
        
        if not os.path.exists(filepath):
            print "Error: Requested config file location does not exist: ", filepath
            return False
        
        # reset internal config vairable to be an empty dict
        self.config = {}
        
        # store the config file location 
        self.filename = filepath
        
        # Create ConfigParser 
        config_parser = ConfigParser.SafeConfigParser()
    
        # load in config file
        results = config_parser.read(filepath)
    
        # if the resutls are empty then we didn't find the config file and should return None
        if len(results) == 0: 
            return False
    
        # Loop through the restuls and build them into a dictionary of settings
        for section_name in config_parser.sections():
            self.config[section_name] = {}
            for option_name in config_parser.options(section_name):
                self.config[section_name][option_name] = config_parser.get(section_name, option_name)
    
        return True

    def init(self, config=None):
        """Reset in-memory copy of config file to empty or to provided dict
        
        If the user passes in a new config dictionary, the in-memory config 
        dict will be replaced with the new config dictionary. If the user does 
        not provide a new config dict then the in-memory config dict is simply 
        emptied. 
        
        Example::
        
            new_config_dict = {}
            new_config_dict["Section"] = {}
            new_config_dict["Section"]["Option"] = "value"
        
            config = Config()
            config.init(new_config_dict)
            config.write(filename='.config')
        
        Args: 
        
            config (dict): New config dictionary to replace current 
                           dictionary. The passed in dict is deep copied and 
                           this object doesn't maintain a reference to the 
                           passed in dictionary object
        
        """
        
        # Reset config dict to empty 
        self.config = {}

        # If user provided a new config object, loop through it and copy it
        # into the internal self.config object to have a separate copy
        if config is not None:
            for section_name in config:
                self.config[section_name] = {}
                for option_name in config[section_name]:
                    self.config[section_name][option_name] = str(config[section_name][option_name])
        
        return

    def write(self, filename=None, force=False):
        """Write out config entries to a file
        
        Dumps in-memory copy of config settings to an ini style config file. 
        If the user passes in a filename here, it is used. If the user omits 
        a filename here, then the filename that was passed in when the 
        Config() object was created will be used. 
        
        Example::
        
            new_config_dict = {}
            new_config_dict["Section"] = {}
            new_config_dict["Section"]["Option"] = "value"
        
            config = Config()
            config.init(new_config_dict)
            config.write(filename='.config')
        
        Args: 
        
            filename (string): Name of ini file to write 
            
            force (bool): Overwrite existing file if present
        
        Returns:
            bool: Returns True if write of config file was successful
        
        """
       
        # if user didn't pass in a filename use one provided when Config() was 
        # created
        if filename is None:
            filename = self.filename

        # if filename is None here, then the user didn't provide a filename 
        # here or when Config() was instanced so fail
        if filename is None:
            print "Error: Could not write config file as no filename was provided"
            return False
            
        # validate filename 
        filepath = os.path.expanduser(filename)
        
        if os.path.isdir(filepath):
            print "Error: Requested config file location is a directory: ", filepath
            return False

        dirpath  = os.path.dirname(filepath)        
        
        # if os.path.dirname() returns an empty string then the directory is 
        # the local PWD 
        if dirpath == '':
            dirpath = '.'

        if not os.path.isdir(dirpath):
            print "Error: directory path to requested config file location "\
                  "does not exist: ", dirpath
            return False
        
        # test to see if the file already exists and don't overwrite unless 
        # told to do so
        if os.path.exists(filepath) and not force:
            print "Error: file already exists: ", filepath
            return False

        # Create ConfigParser 
        config_parser = ConfigParser.SafeConfigParser()
        
        # loop through config
        # add the section to the config_parser 
        # loop through the section and add options to the config_parser
        for section_name in self.config:
            config_parser.add_section(section_name)
            for option_name in self.config[section_name]:
                config_parser.set(section_name, option_name, str(self.config[section_name][option_name]))

        # Write out config parser to desired file
        with open(filepath, 'wb') as fp:
            config_parser.write(fp)
        
        return True


class _DB():
    """An internal class to hold common database functionality
    
    This class is meant to be subclassed by a specific database wrapper class. 
    This class simply holds the functionality that is common among multiple 
    database types. For example, loading a config file is common among all 
    database wrapper objects. So is creating an ssh tunnel.
    
    """
    
    def __init__(self):
        
        self.tunnel = None
        self.config = None        
        self.dbclient = None
                    
        return 
        
    def load(self, filename):
        """Load the config file into memory
        
        This simply loads the config file into memory. It does not attempt to 
        extract any values from the config file.
        
        Args: 
        
            filename (string): filename for config file
        
        Returns: 
        
            (bool): Returns True if config file was successfully loaded
            
        """
        
        self.config = Config(filename=filename)
        rv = self.config.load()
        
        return rv

    def sshtunnel_create(   self,
                            ssh_host,
                            ssh_port,
                            ssh_username,
                            ssh_key_file,
                            remote_port,
                            local_port):                            
        """Creates an SSH tunnel for the database connection to travel over
        
        Args: 
        
            ssh_host (string): The server address ('db.someserver.com')
            
            ssh_port (int): The ssh port to connect using (i.e. 22)
            
            ssh_username (string): The username to use for the ssh connection
            
            ssh_key_file (string): The filename of the ssh key to use 
                                   (no passphrase)
            
            remote_port (int): The remote port number for the tunnel 
            
            local_port (int): The local port number for the tunnel        
        
        Returns: 
        
            (bool): Returns True if the ssh tunnel was successfully created
        
        
        """
        #print ssh_host, ssh_port, ssh_username, ssh_key_file, remote_port, local_port

        # STEP 1
        # try to create the tunnel object
        try:
            self.tunnel = sshtunnel.SSHTunnelForwarder(
                            ssh_address_or_host=(ssh_host, ssh_port),
                            ssh_username=ssh_username,
                            ssh_private_key=ssh_key_file,
                            remote_bind_address=("127.0.0.1", remote_port),
                            local_bind_address=("0.0.0.0", local_port))
        except sshtunnel.BaseSSHTunnelForwarderError as e:
            print "Error: Could not create sshtunnel object: " + e.message
            self.tunnel = None
            return False

        # STEP 2
        # try to start the tunnel
        try:
            self.tunnel.start()
        except sshtunnel.BaseSSHTunnelForwarderError as e:
            print "Error: Could not start sshtunnel: " + e.message
            self.tunnel = None
            return False        
                
        return True

    def client(self):
        """Gets the client database object.
        
        Returns:
        
            The raw database client object
        
        """
        
        return self.dbclient    
                

class Mongo(_DB):
    """Thin wrapper for MongoDB
    
    This is a thin wrapper to manage a connection to MongoDB. Mainly this 
    serves as an easy way to load connection parameters from an ini style 
    config file. This class also provides the ability to use an SSH tunnel to 
    allow connection to a database that is located out over the internet or an 
    unsecure network connection. 
    
    The basic theory of operations is to:
    
    #. Instance the Mongo object with a config filename
    #. run connect()
    #. get the raw client object using client()
    #. perform database actions using raw client object 
    #. run disconnect()
    
    If a config filename is passed to the constructor and is successfully auto 
    loaded, then the constructor will automatically run configure() so the 
    user doesn't have to run it separately. But if the constructor is run 
    without a config filename or with auto_load_config_file set to False, then 
    the user will need to explicitly run configure(). 
    
    Example using a config file::
    
        db = Mongo(config_filename='.foilmongo')
        db.connect()        
        client = db.client()
        <perform db actions using raw pymongo client object>
        db.disconnect()        
    
    Example without a config file::
    
        db = Mongo(auto_load_config_file=False)
        db.configure(   address='localhost',
                        port=27017,
                        timeout_ms=30000,
                        use_ssh_tunnel=False,
                        ssh_host=None,
                        ssh_port=None,
                        ssh_username=None,
                        ssh_key_file=None,
                        remote_port=None)
        db.connect()        
        client = db.client()
        <perform db actions using raw pymongo client object>
        db.disconnect()        
        
    Args: 

        auto_load_config_file (bool): If True, the constructor will attempt to 
                                      load a config file with all the database 
                                      configuration parameters. If False, then 
                                      the config file will not be loaded 
                                      immediately and the user will need to 
                                      manually set the configuration 
                                      parameters with the configure() method 
                                      or load a config file with the load() 
                                      method and provide a config filename.
    
        config_filename (string): Filename of an ini style configuration file 
                                  that has all the database connection 
                                  parameters.         
        
    """
    
    def __init__(   self,
                    auto_load_config_file=True,
                    config_filename=None):
                    
        _DB.__init__(self)
        
        # Set defaults and store parameters
        self.address = None
        self.port = None
        self.timeout_ms = None
        self.use_ssh_tunnel = None
        self.ssh_username = None
        self.ssh_port = None
        self.remote_port = None
        self.ssh_key_file = None
        self.dbtype = 'MongoDB'        
        
        self.default_config_file_locations = ['database.ini', '~/.database.ini']
        self.config_filename = config_filename
        self.auto_load_config_file = auto_load_config_file
        
        # If no config file is provided use these as the defaults
        # that would then be used to write out a template config file so the 
        # user could then edit it with the real settings
        self.config_defaults = {}
        self.config_defaults["MongoServer"] = {}
        self.config_defaults["MongoServer"]["address"] = "localhost"
        self.config_defaults["MongoServer"]["port"] = "27017"
        self.config_defaults["MongoDatabase"] = {}
        self.config_defaults["MongoDatabase"]["database_name"] = "foil"        
        self.config_defaults["MongoClient"] = {}
        self.config_defaults["MongoClient"]["serverselectiontimeoutms"] = 5000        
        self.config_defaults["SSHTunnel"] = {}
        self.config_defaults["SSHTunnel"]["use_ssh_tunnel"] = "False"
        self.config_defaults["SSHTunnel"]["ssh_host"] = 'someserver.com'
        self.config_defaults["SSHTunnel"]["ssh_port"] = 22
        self.config_defaults["SSHTunnel"]["ssh_username"] = "user"
        self.config_defaults["SSHTunnel"]["remote_port"] = 27017
        self.config_defaults["SSHTunnel"]["ssh_key_file"] = os.path.expanduser('~/.ssh/ssh_key')            
        
        # If auto load has not been specifically disabled by user attempt 
        # to load the config file
        # If the user passed in a specific filename, use that one
        # otherwise cycle through default config file location options
        # until one is successfully loaded        
        if self.auto_load_config_file:
            if self.config_filename is not None:
                rv = self.load(self.config_filename)
                if rv:
                    self.configure()
            else:
                for filename in self.default_config_file_locations:
                    if self.load(filename):
                        break
        
        return
    
    def __del__(self):
        """Deconstructor to make sure the sshtunnel is closed and doens't hang
                
        """
        
        self.disconnect()
        
        return
    
    def configure(      self,
                        address='localhost',
                        port=27017,
                        timeout_ms=30000,
                        use_ssh_tunnel=False,
                        ssh_host=None,
                        ssh_port=None,
                        ssh_username=None,
                        ssh_key_file=None,
                        remote_port=None):
        """Set database connection parameters
        
        This method sets the database connection parameters needed to make a 
        database connection. To configure, the user must either provide the 
        needed parameters to this method, or the user must have previously 
        provided a config file through the Mongo() constructor or the load() 
        method. 
        
        If a config file was provided, this method attempts to extract the 
        needed parameters from the loaded config file. If a config file was 
        not provided then the parameters passed into this function will be 
        used.
        
        This method must be run prior to calling connect()
        
        Args: 
        
            address (string): the url for the database server (db.example.com)
            
            port (int): The port number the database is listening on (27017)
            
            timeout_ms (int): The timeout window to wait for the database to 
                              respond
            
            use_ssh_tunnel (bool): If True, an ssh tunnel will be created to 
                                   the database and the db client connection 
                                   will be made through this tunnel
        
            port (int): The local port number for the database
        
            ssh_host (string): The server address ('db.someserver.com')
            
            ssh_port (int): The ssh port to connect using (i.e. 22)
            
            ssh_username (string): The username to use for the ssh connection
            
            ssh_key_file (string): The filename of the ssh key to use 
                                   (no passphrase)
            
            remote_port (int): The remote port number for the tunnel                 
        
        """
    
        # if the config file has been loaded attempt to pull configuration 
        # parameters from the config dict
        if self.config:
            try:
                self.address = self.config.get("MongoServer", "address")
            except KeyError as e:
                pass
            
            try:
                self.port = self.config.get("MongoServer", "port", casttype='int')
            except KeyError as e:
                pass
        
            try:
                self.timeout_ms = self.config.get("MongoClient", "serverselectiontimeoutms", casttype='int')
            except KeyError as e:
                pass

            try:
                self.use_ssh_tunnel = self.config.get("SSHTunnel", "use_ssh_tunnel", casttype='bool')
            except KeyError as e:
                pass
        
            try: 
                self.ssh_host = self.config.get("SSHTunnel", "ssh_host")
            except KeyError as e:
                pass

            try:
                self.ssh_port = self.config.get("SSHTunnel", "ssh_port", casttype='int')
            except KeyError as e:
                pass

            try: 
                self.ssh_username = self.config.get("SSHTunnel", "ssh_username")
            except KeyError as e:
                pass

            try: 
                self.ssh_key_file = self.config.get("SSHTunnel", "ssh_key_file")
            except KeyError as e:
                pass

            try: 
                self.remote_port = self.config.get("SSHTunnel", "remote_port", casttype='int')
            except KeyError as e:
                pass
        else:
            # if a config file isnt' being used then set config parameters to 
            # passed in parameters or defaults 
            self.address = address
            self.port = port
            self.timeout_ms = timeout_ms        
            self.use_ssh_tunnel = use_ssh_tunnel        
            self.ssh_host = ssh_host
            self.ssh_port = ssh_port
            self.ssh_username = ssh_username        
            self.ssh_key_file = ssh_key_file
            self.remote_port = remote_port
                
        return
    
    def connect(self):
        """Initiate a connection to the backend database
        
        Creates a connection to the backend database using the db client. If 
        the user has requested an ssh tunnel be used it is created here. Once 
        the connection is made, this method attempts to access the database to 
        validate the connection was truly successful.
        
        Returns:
            (bool): Returns True if a connection to the database was 
                    successfully established.
        
        """    
        
        # STEPS
        # 1. Verify minimum needed connection parameters have been provided 
        # 2. Create ssh tunnel if needed 
        # 3. Extablish database connection using raw DB client
        # 4. Verify database connection by attempting a read only action
        
        # STEP 1: 
        # Verify minimum needed connection parameters have been provided
        # minimally we need the address and the port and the timeout
        if self.address == None: 
            print "Error: Cannot Connect. No address set"
            return False

        if self.port == None: 
            print "Error: Cannot Connect. No port set"
            return False
    
        if self.timeout_ms == None: 
            print "Error: Cannot Connect. No timeout_ms set"
            return False
        
        # STEP 2
        # Create ssh tunnel if needed
        if self.use_ssh_tunnel:
            self.sshtunnel_create( ssh_host=self.ssh_host,
                                   ssh_port=self.ssh_port,
                                   ssh_username=self.ssh_username,
                                   ssh_key_file=self.ssh_key_file,
                                   remote_port=self.remote_port,
                                   local_port=self.port)
                                        
            if self.tunnel is None:
                print "Error: Could not create ssh tunnel"
                return False
            
        # STEP 3
        # Extablish database connection using raw DB client
        self.dbclient = pymongo.MongoClient(self.address,
                                            self.port,
                                            serverSelectionTimeoutMS = self.timeout_ms)
    
        if self.dbclient is None:
            print "Error: Could not establish database client"
            return False
    
        # STEP 4
        # Verify database connection by attempting a read only action
        try:
            self.dbclient.server_info()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            print "Error: Could not verify connection to database server:" + e.message
            return False
        else:
            #print "Database connection: Successful"
            pass
    
        return True

    def disconnect(self):
        """Close the connection to the database
        
        Closes the client connection to the backend database as well as closes 
        the ssh tunnel if one was established
        
        """
                
        if self.dbclient:
            self.dbclient.close()
            self.dbclient = None
        
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None
        
        return


class SelfTest():
    """A class to perform tests on the Foil package
    
    Instantiating the SelfTest class does not perform any actions. To run the 
    tests, use the run() function which will parse CLI input parameters. 
    
    Args:
        None:

    """
    
    def __init__(self):
        
        self.args = None        
        self.tests = []
        self.tests.append(self._test_initconfigfile)
        self.tests.append(self._test_loadconfigfile)
        self.tests.append(self._test_connectmongodb)
                        
        return
        
    def _parser(self):
        """Function to parse CLI arguments"""
        
        desc = 'Foil Library Self Test'
        parser = argparse.ArgumentParser(description=desc)

        parser.add_argument(    '-n',
                                '--testnum',
                                required=False, 
                                action='store',
                                help='Test Num')       

        parser.add_argument(    '-i',
                                '--init',
                                required=False,
                                action='store_true',
                                help='Generate default config file')
        
        parser.add_argument(    '-f',
                                '--filename',
                                required=False,
                                action='store',
                                help='Config filename to use')
        
        parser.add_argument(    '-l',
                                '--list',
                                required=False,
                                action='store_true',
                                help='List available tests to run')
        
        self.args = vars(parser.parse_args())
        
        return        

    def run(self):
        """Run the self test application using CLI parameters"""
        
        # STEPS:
        # 1. run CLI parser
        # 2. Print list of tests if requested and then quit
        # 3. Determine test num and run requested actions
        # 4. Perform other requested actions
        
        # STEP 1 
        # run CLI argument parser
        self._parser()
        
        # STEP 2
        # Print list of tests if requested and then quit
        if self.args['list']:
            print 'Available tests:'
            for i,t in enumerate(self.tests):
                print str(i) + ": " + str(t.__name__)[6:]
        
            quit()

        # STEP 3
        # determine test numebr to run
        # if the user did enter something, try and convert to an int
        if self.args['testnum'] is not None:
            try: 
                self.args['testnum'] = int(self.args['testnum'])
            except ValueError as e: 
                print 'Error: Invalid test num. '\
                      'Entry must be a number' + \
                      e.message
                quit()
        
            if self.args['testnum'] > (len(self.tests)-1):
                print "Error: Requested test num is out of range. '\
                      'Num available tests: " + \
                      str(len(self.tests))
                quit()
        
            # run requested test
            test_num = self.args['testnum']
            test_function = self.tests[test_num]
            test_function()
        
        # STEP 4
        # Perform other requested actions
        if self.args['init']:

            # need a DB object to get a copy of the default config entries
            db = Mongo(auto_load_config_file=False)
        
            # create the config obejct
            config = Config()
        
            # initialize the Config with the default entries from foil
            config.init(db.config_defaults)
        
            # set default filename
            filename = '.foilmongo'
            
            # if the user passed in a filename on the command line use that
            # filename
            if self.args['filename'] is not None:
                filename = self.args['filename']
        
            # write out the Config to a file
            config.write(filename=filename)
                    
        return     

    def _test_initconfigfile(self):
        """Example code to show how to initialize and write out a config file"""

        # need a foil object to get a copy of the default config entries
        db = Mongo(auto_load_config_file=False)
        
        # create the config obejct
        config = Config()
        
        # initialize the Config with the default entries from foil
        config.init(db.config_defaults)

        # set default filename
        filename = '.foilmongo'
        
        # if the user passed in a filename on the command line use that
        # filename
        if self.args['filename'] is not None:
            filename = self.args['filename']        
        
        # write out the Config to a default file
        config.write(filename=filename)
        
        return

    def _test_loadconfigfile(self):
        """Example code to show how to load a config file"""

        # set default filename
        filename = '.foilmongo'
        
        # if the user passed in a filename on the command line use that
        # filename
        if self.args['filename'] is not None:
            filename = self.args['filename']
        
        config = Config(filename=filename)
        
        rv = config.load()
        if rv:
            print "Config load was successful"
        else:
            print "Config load failed"
            quit()
        
        print "Sections:" 
        for section in config.config:
            print '[' + section + ']'
            for option in config.config[section]:
                print option + '=' + config.get(section,option)
        
        return        
        
    def _test_connectmongodb(self):
        """Example code to show how to connect to MongoDB"""

        # set default filename
        filename = '.foilmongo'
        
        # if the user passed in a filename on the command line use that
        # filename
        if self.args['filename'] is not None:
            filename = self.args['filename']

        db = Mongo(config_filename=filename)
        db.connect()
        client = db.client()
        db.disconnect()
        
        return            

if __name__ == '__main__':
    SelfTest().run()
    

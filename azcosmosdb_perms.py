#!python3
import subprocess
import shlex
import sys
import json
import re

class SQLSyntaxError(Exception):
    pass
class SQLValueError(Exception):
    pass

# get command line parameters (assume key val )
# debug: debug level (0 - no extra prints, )
P = {"debug" : "0", "print_az": "0", "script_file" : "test3.sql"}
for i in range(int((len(sys.argv)-1)/2)):
    P[sys.argv[2*i+1]] = sys.argv[2*i+2]
for key in P.keys():
    if (re.match("^\d+", P[key])):
        P[key] = int(P[key])
SHOWAZCMD = (P["print_az"] > 0)


# hold variables used for context for calls
# eg, USE ACCOUNT cosmosdb_account
# eg, USE DATABASE [cosmosdb_account.]database_name
E = {"account": "", "database": "", "exit_on_error" : 1}

# reserved words
RESERVED_WORDS=["create", "databases", "describe", "exitonerror", "grant", "grants"
    , "list", "noexitonerror", "on", "role", "roles", "to", "use", "datareader", "datacontributor"]

# some aliases for predefined ROLES
ROLE_TO_ALIAS = {"Cosmos DB Built-in Data Reader":"datareader",  "Cosmos DB Built-in Data Contributor" : "datacontributor"}
ALIAS_TO_ROLE = {val:key for key,val in ROLE_TO_ALIAS.items()}

# dictionary of avail privileges for role to alias
PRIV_TO_ALIAS = {
    "Microsoft.DocumentDB/databaseAccounts/readMetadata" :"readmetadata"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/create" : "createitem"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read" : "readitem"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/replace" : "replaceitem"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/upsert" : "upsertitem"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/delete" : "deleteitem"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery" : "query"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/readChangeFeed" : "readchangefeed"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeStoredProcedure" : "execute"
, "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/manageConflicts" : "manageconflicts"
}

# alias of allowed privilege actions, along with any custom composite aliases
ALIAS_TO_PRIV = {val:[key] for key,val in PRIV_TO_ALIAS.items()}
ALIAS_TO_PRIV["select"] = ["Microsoft.DocumentDB/databaseAccounts/readMetadata" 
    , "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read"
    , "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery"]
ALIAS_TO_PRIV["allitem"] = ["Microsoft.DocumentDB/databaseAccounts/readMetadata" 
    , "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"]
ALIAS_TO_PRIV["all"] = ["Microsoft.DocumentDB/databaseAccounts/readMetadata" 
    , "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*"
    , "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"]

# flush output 
sys.stdout.reconfigure(line_buffering=True) 

# print out debug statements
def dodebug(p_level, p_str):
    if (p_level <= P["debug"]):
        print(p_str)

# print table format from json array
def print_jsonarray_table(p_json_array, p_cols_array):
    cw = [] # col width
    tblwidth = 0
    # get max len of each column
    for i in range(len(p_cols_array)):
        cw.append(len(p_cols_array[i]))
        for j in p_json_array:
            if (len(j[p_cols_array[i]]) > cw[i]): cw[i] = len(j[p_cols_array[i]])
        tblwidth += cw[i]
    tblwidth += len(cw)*3 + 1
    sep = " " + "-"*tblwidth
    
    print(sep)
    line = " |"
    for i in range(len(cw)):
        line += " {:{}} |".format(p_cols_array[i], cw[i])
    print(line)
    print(sep)

    for j in p_json_array:
        line = " |"
        for i in range(len(cw)):
            line += " {:{}} |".format(j[p_cols_array[i]], cw[i])
        print(line)
    print(sep)

# run azure command
# p_cmd: command line execution (eg, az version)
# p_raise_error: True/False.  if result returncode <> 0, will raise a SQLValue error 
# p_json_on_success: return stdout of command in json format
# p_print_cmd: whether or not to printout the command
# return value: if success && json_on_succes=True, then json of stdout.  Else full output
def run_az_cmd (p_cmd, p_raise_error = True, p_json_on_success = True, p_print_cmd = False):
    if (p_print_cmd or P["debug"] > 0): print(f"* {p_cmd}")
    r=subprocess.run(p_cmd, shell = True, capture_output=True)
    dodebug(3, "Output is: {}".format(r.stdout))
    if (r.returncode != 0 and p_raise_error):
        raise SQLValueError(r.stderr)
    if (r.returncode == 0 and p_json_on_success):
        return bstr2json(r.stdout)
    return r

def bstr2json(p_str):
    return json.loads(p_str.decode('utf8'))

# make sure we are logged into azure and valid version of az cli
def check_version_and_login():
    j = run_az_cmd("az version")
    v = j["azure-cli"].split(".")
    if ((int(v[0]) < 2) or (int(v[0]) == 2 and int(v[1]) < 24)):
        raise SQLValueError("Require az cli version 2.24 or greater (you are running {})".format(j["azure-cli"]))
    j = run_az_cmd("az account show")
    print("Working with account:\n  User        : {}\n  Subscription: {}\n".format(j['user']['name'], j['name']))

# get cosmosdb account.  Raise error if not found
# return json obj for account
def get_cosmosdb_account(acct_name):
    cmd = "az cosmosdb list --query \"[?name=='{}']\"".format(acct_name)
    j = run_az_cmd(cmd)
    if (len(j) == 1):
        return j[0]
    elif (len(j) == 0):
        raise SQLValueError("Cosmos DB Account {} does not exist in this subscription or you do not have access.".format(acct_name))
    else:
        raise SQLValueError("Multiple Cosmos DB accounts match {}".format(acct_name))

# get the database. Raise error if not found
# return json obj for database
def get_database(dbname):
    acct = validate_account()
    j = run_az_cmd("az cosmosdb sql database list --account-name {} --resource-group {} --query \"[?name=='{}']\"".format(acct["name"], acct["resourceGroup"],dbname))
    if (len(j) == 1):
        return j[0]
    if (len(j) == 0):
        raise SQLValueError("Database '{}' does not exist cosmos account {} or you do not have access.".format(dbname, acct["name"]))
    else:
        raise SQLValueError("Multiple databases match {}".format(dbname))

# get a container. Raise error if not found
# return json obj for container
def get_container(dbname, container_name):
    acct = validate_account()
    j = run_az_cmd("az cosmosdb sql container list --account-name {} --resource-group {} --database-name {} --query \"[?name=='{}']\"".format(acct["name"], acct["resourceGroup"], dbname, container_name))
    if (len(j) == 1):
        return j[0]
    if (len(j) == 0):
        raise SQLValueError("Container '{}' does not exist in database {} or you do not have access.".format(dbname, container_name))
    else:
        raise SQLValueError("Multiple containers match {}".format(container_name))

# get user upn from an id
def get_user_from_id(userid):
    return run_az_cmd("az ad user show --id {} --query userPrincipalName --output json".format(userid))

# get role name from a role id
def get_role_from_id(roleid):
    acct = validate_account()
    return run_az_cmd("az cosmosdb sql role definition show --account-name {} --resource-group {} --id {} --query roleName --output json".format(acct["name"], acct["resourceGroup"],roleid))

# returns array of json obj for roles
# p_role_name: role to match... if not passed, returns all rows in current account
def get_roles(p_role_name = "", p_print_az_cmd = False):
    acct = validate_account()
    p_role_name = p_role_name if (p_role_name.lower() not in ALIAS_TO_ROLE) else ALIAS_TO_ROLE[p_role_name.lower()]
    q = "--query \"[?roleName=='{}']\"".format(p_role_name) if (p_role_name) else ""
    return run_az_cmd("az cosmosdb sql role definition list --account-name {} --resource-group {} {}".format(acct["name"], acct["resourceGroup"], q)
        , p_print_cmd = p_print_az_cmd)

# return array of json obj for role assignments
# p_role_id:
# p_user_id:
# p_scope: scope of role assignment, if any
def get_role_assignment(p_role_id, p_user_id, p_scope):
    acct = validate_account()
    role_def_id = p_role_id if (p_role_id[0] == "/") else acct["id"] + "/sqlRoleDefinitions/" + p_role_id
    q="[?scope=='{}' && principalId=='{}' && roleDefinitionId=='{}'].{{name:name}}".format(acct["id"] + ("" if p_scope=="/" else p_scope)
        , p_user_id, role_def_id)
    j = run_az_cmd("az cosmosdb sql role assignment list --account-name {} --resource-group {} --query \"{}\"".format(acct["name"], acct["resourceGroup"],q))
    return j

# check to see if a specific role assignment exists
# returns True/False
def exists_role_assignment(p_role_id, p_user_id, p_scope):
    j = get_role_assignment(p_role_id, p_user_id, p_scope)
    return (len(j)>0)

# given commands in a string, execute them 
def run_script(p_script):
    lines = re.split("\n", p_script)
    for i in range(len(lines)):
        # skip empty or comment lines
        if ((not re.match("[^\s]", lines[i]) ) or re.match("^\s*\-\-", lines[i])):
            print(lines[i])
            continue
        print("[{}]> {}".format(current_context_string(),lines[i]))        
        try:
            parse_sql_command(lines[i])
        except SQLSyntaxError as e:
            print("Syntax error at line {}:\n  {}\n{}".format(i+1, lines[i], e))
            if (E["exit_on_error"]):
                raise e
        except SQLValueError as e:
            print("Value error at line {}:\n  {}\n{}".format(i+1, lines[i], e))
            if (E["exit_on_error"]):
                raise e


# return default path in text (set by USE command)
def current_context_string():
    path = ""
    if (E["account"]):
        path = E["account"]["name"]
    if (E["database"]):
        path = path + "." + E["database"]["name"]
    return path

# get the scope relative to cosmosdb account
# (ie, strips out account id from the scope)
def relative_scope(scope):
    rel_scope = scope.replace(E["account"]["id"], "", 1)
    if (not rel_scope): rel_scope= "/"
    return rel_scope



# return the current scope of the commands
# this is a combination of what was done by the USE command as well as the passed path
# path: [[<dbname>.]<container_name>]
#/dbs/<database-name>/colls/<container-name> 
def get_scope(path):
    scope="/"
    if (not path):
        if (E["database"]):
            scope = "/dbs/" + E["database"]["name"]
    else:
        a = path.split(".")
        if (len(a) == 1):
            if (E["database"]):  # path is container since db is set
                coll = get_container(E["database"]["name"], path)
                scope = "/dbs/" + E["database"]["name"] +"/colls/"+path
            else:
                db = get_database(path)
                scope="/dbs/"+db["name"]
        elif (len(a) == 2):
            if (E["database"]):
                raise SQLValueError("Already in database.  Cannot be specified in {}", path)
            db = get_database(a[1])
            coll = get_container(db["name"], a[1])
            scope="/dbs/"+db["name"]+"/colls/"+coll["name"]
    return scope

# parse a line of sql & dole out work to proper function
# raises Exceptions for syntax errors
def parse_sql_command(p_str):
    mysplitter = shlex.shlex(p_str, posix=True)
    mysplitter.whitespace += ","
    mysplitter.whitespace_split = True
    args = list(mysplitter)
    for i in range(len(args)):
        if (args[i].lower() in RESERVED_WORDS):
            args[i] = args[i].lower()
    s = " ".join(args)
    if (args[0] == "use"):
        if (len(args) > 2):
            raise SQLSyntaxError("Syntax: USE [<cosmosdb_acct>[.<database_name>]]")
        do_use(*args[1:])
    elif (args[0] == "create"):
        if (re.match("^create role .* with .*",s)):
            on_index = -1 if (args.count("on") == 0) else args.index("on")
            if (on_index >= 0):
                do_create_role(args[2], args[4:on_index], args[on_index+1])
            else:
                do_create_role(args[2], args[4:], "")
        else:
            raise SQLSyntaxError("Syntax: CREATE ROLE <role> WITH <permission> [<permission> ...] [ON <database name>[.<collection>]")
    elif (args[0] == "list"):
        if (s=="list roles"):
            do_list_roles()
        elif (s=="list databases"):
            do_list_databases()
        elif (s=="list grants"):
            do_list_grants()
        elif (s=="list collections"):
            do_list_collections()
        else:
            raise SQLSyntaxError("Syntax: LIST (COLLECTIONS|DATABASES|GRANTS|ROLES)")
    elif (args[0] == "grant"):
        if (len(args) == 5 and args[1] == "role" and args[3] == "to"):
            do_grant_role(args[2], args[4], "")
        elif (len(args) == 7 and args[1] == "role" and args[3] == "to" and args[5] == "on"):
            do_grant_role(args[2], args[4], args[6])
        elif (re.match("^grant \w.* to role \w.*", s)):
            pass
        else:
            raise SQLSyntaxError("Syntax:\nGRANT ROLE <roleName> TO <user> [ON <scope>]\nGRANT <permission> TO ROLE <roleName>")
    elif (args[0] == "revoke"):
        if (len(args) == 5 and args[1] == "role" and args[3] == "from"):
            do_revoke_role(args[2], args[4], "")
        elif (len(args) == 7 and args[1] == "role" and args[3] == "from" and args[5] == "on"):
            do_revoke_role(args[2], args[4], args[6])
        elif (re.match("^grant \w.* to role \w.*", s)):
            pass
        else:
            raise SQLSyntaxError("Syntax:\nREVOKE ROLE <roleName> FROM <user> [ON <scope>]\nREVOKE<permission> FROM ROLE <roleName>")
    elif (args[0] == "describe"):
        if (len(args) == 3 and args[1] == "role"):
            do_describe_role(args[2])
        else:
            raise SQLSyntaxError("Syntax:\nDESCRIBE ROLE <roleName>")      
    elif (args[0] == "drop"):
        if (args[1] == "role" and len(args) == 3):
            do_drop_role(args[2])
        else:
            raise SQLSyntaxError("Syntax:\nDROP ROLE <roleName>")
    elif (args[0] == "exitonerror"):
        E["exit_on_error"] = 1
    elif (args[0] == "noexitonerror"):
        E["exit_on_error"] = 0
    else:
        raise SQLSyntaxError("Unknown command: {}".format(args[0]))

# make sure account is already set, if not raise error
# return value: cosmosdb account json 
def validate_account():
    if (not E["account"]):
        raise SQLValueError("Syntax error. Cosmos DB account not specified.")
    return E["account"]

# set the current context of the session
def do_use(context_path = ""):
    acct = ""
    a = context_path.split(".")
    if (context_path):
        # check that account exists
        acct = get_cosmosdb_account(a[0])
    E["account"] = acct

    # set the database if passed
    database = ""
    if (len(a) > 1):
        database=get_database(a[1])

    # set this as the environment
    print("~ Set account to {}".format(acct["name"]))
    if (database):
        E["database"] = database
        print("~ Set database to {}".format(database["name"]))

# list roles defined in the current account
def do_list_roles():
    acct = validate_account()
    j = get_roles(p_print_az_cmd=SHOWAZCMD)
    if (len(j) == 0):
        print("~ No roles found")
    else:
        print("~ Roles in account {}".format(acct["name"]))
        print_jsonarray_table(j, ["name", "roleName"])

# list databases [acct]
def do_list_databases():
    acct = validate_account()
    j = run_az_cmd("az cosmosdb sql database list --account-name {} --resource-group {}".format(acct["name"], acct["resourceGroup"])
        , p_print_cmd = SHOWAZCMD)
    if (len(j) == 0):
        print("~ No databases found")
    else:
        print("~ Databases in account {}".format(acct["name"]))
        print_jsonarray_table(j, ["name"])

#az cosmosdb sql role assignment list --account-name --resource-group
def do_list_grants():
    acct = validate_account()
    j = run_az_cmd("az cosmosdb sql role assignment list --account-name {} --resource-group {}".format(acct["name"], acct["resourceGroup"])
        , p_print_cmd = SHOWAZCMD)
    if (len(j) == 0):
        print("~ No grants found")
    else:
        for g in j:
            g["User"] = u = get_user_from_id(g["principalId"])
            g["Role"] = r = get_role_from_id(g["roleDefinitionId"])
            g["Scope"] = s = relative_scope(g["scope"])
        print_jsonarray_table(j, ["User", "Role", "Scope"])

def do_list_collections():
    acct = validate_account()
    db = E["database"]
    if (not db):
        print(" ~ Current database context not set.  Set with call to USE <acctname>.<dbname>")
        return

    j = run_az_cmd("az cosmosdb sql container list --account-name {} --resource-group {} --database-name {}".format(acct["name"]
        , acct["resourceGroup"], db["name"]), p_print_cmd=SHOWAZCMD)
    if (len(j) == 0):
        print("~ No collections found or you do not have access")
    else:
        print("~ Collections in database")
        print_jsonarray_table(j, ["name"])

def do_grant_role(p_role, p_user, p_scope = ""):
    acct = validate_account()

    # check the role exists cmd = "az cosmosdb list --query \"[?name=='{}']\"".format(acct_name)
    j = get_roles(p_role)
    if (len(j) == 0):
        raise SQLValueError("Did not find role {} in account {}".format(p_role, acct["name"]))
    role_id = j[0]["name"]

    # get the user ids we will use
    j = run_az_cmd("az ad user list --upn \"{}\" --query \"[].{{objectId:objectId}}\"".format(p_user))
    if (len(j) == 0):
        raise SQLValueError("Did not find user {} in directory".format(p_user))
    user_id = j[0]["objectId"]

    # determine the scope
    scope = get_scope(p_scope)

    # warn if grant already exists and do nothing
    if (exists_role_assignment(role_id, user_id, scope)):
        print("~ Warning: grant already exists... doing nothing")
        return

    # grant the role
    cmd = 'az cosmosdb sql role assignment create --account-name {} --resource-group {} --principal-id {} ' \
        + ' --role-definition-id "{}" --scope "{}" '
    j = run_az_cmd(cmd.format(acct["name"], acct["resourceGroup"], user_id, role_id, scope), p_print_cmd=SHOWAZCMD)
    print("~ Granted role")

# delete role assignment (if it exists)
def do_revoke_role(p_role, p_user, p_scope = ""):
    acct = validate_account()

    # check the role exists cmd = "az cosmosdb list --query \"[?name=='{}']\"".format(acct_name)
    j = get_roles(p_role)
    if (len(j) == 0):
        raise SQLValueError("Did not find role {} in account {}".format(p_role, acct["name"]))
    role_id = j[0]["name"]

    # get the user ids we will use
    j = run_az_cmd("az ad user list --upn \"{}\" --query \"[].{{objectId:objectId}}\"".format(p_user))
    if (len(j) == 0):
        raise SQLValueError("Did not find user {} in directory".format(p_user))
    user_id = j[0]["objectId"]

    # determine the scope
    scope = get_scope(p_scope)

    # check if the role assignment exists
    j = get_role_assignment(role_id, user_id, scope)
    if (len(j) ==0):
        print("~ Warning: grant does not exists... doing nothing")
        return

    # delete the role assigment
    for roleAssignment in j:
        run_az_cmd("az cosmosdb sql role assignment delete --account-name {} --resource-group {} --role-assignment-id {} --yes ".format(acct["name"]
            , acct["resourceGroup"], roleAssignment["name"]) , p_json_on_success=False, p_print_cmd = SHOWAZCMD)
        print("~ Revoked role")

# create a role
#az cosmosdb sql role definition create --account-name MyAccount --resource-group MyResourceGroup --body @role-definition.json
def do_create_role(p_role_name, p_privs, p_scope = ""):
    acct = validate_account()

    # make sure role does not exist
    j = get_roles(p_role_name)
    if (len(j) > 0):
        raise SQLValueError("Role {} already exists in account {}".format(p_role_name, acct["name"]))

    # add in the privs
    dataActions = []
    for perm_alias in p_privs:
        if (perm_alias == ","):   # ignore separator
            continue
        if (perm_alias.lower() not in ALIAS_TO_PRIV):
            raise SQLValueError("Permission {} is not defined".format(perm_alias))
        for perm_name in ALIAS_TO_PRIV[perm_alias.lower()]:
            if (perm_name not in dataActions):
                dataActions.append(perm_name) 
    
    # create the role def json
    j = {"RoleName":p_role_name, "Type" : "CustomRole", "AssignableScopes" : [get_scope(p_scope)]
        , "Permissions" : [{"DataActions" : dataActions} ]} 
            
    cmd="az cosmosdb sql role definition create --account-name {} --resource-group {} --body \"{}\"".format(
        acct["name"], acct["resourceGroup"], j)
    r = run_az_cmd(cmd, p_json_on_success=False,p_print_cmd=SHOWAZCMD)
    print(f"Created role {p_role_name}")

def do_describe_role(p_role_name):
    acct = validate_account()
    j = get_roles(p_role_name, p_print_az_cmd=True)
    if (len(j) == 0): 
        print("~ WARNING: role {} not found in this account".format( p_role_name))
        return
    r = j[0]
    print("  Role: {}   Scope: {}".format(p_role_name, relative_scope(r["assignableScopes"][0])))
    privs = [ {"privilege":priv} for priv in r["permissions"][0]["dataActions"] ]
    print_jsonarray_table(privs, ["privilege"])

# drop a role
#az cosmosdb sql role definition create --account-name MyAccount --resource-group MyResourceGroup --body @role-definition.json
def do_drop_role(p_role_name):
    acct = validate_account()

    j = get_roles(p_role_name)
    if (len(j) == 0):
        raise SQLValueError("Role {} does not exist in account {}".format(p_role_name, acct["name"]))

    # can't delete builtin role
    if (j[0]["typePropertiesType"] != "1"):
        raise SQLValueError("Role {} is a builtin role.  Cannot delete it.".format(p_role_name))
    
    cmd="az cosmosdb sql role definition delete --account-name {} --resource-group {} --id {}  --yes".format(
        acct["name"], acct["resourceGroup"], j[0]["name"])

    r = run_az_cmd(cmd, p_json_on_success=False, p_print_cmd=SHOWAZCMD)
    print("~ Dropped role {}".format(p_role_name))

check_version_and_login()

#run_script("use cosmosdbacct01\ndescribe role datacontributor\ndescribe role datareader\n")
#exit (0)

with open(P["script_file"]) as fp:
    script = fp.read()
    run_script(script)

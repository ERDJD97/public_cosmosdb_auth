# Azure CosmosDB Perms

- [Background](#background)
- [Environment Setup](#environment-setup)
- [Testing Method and Results](#testing-method-and-results)
- [SQL Syntax](#sql-syntax)

## Background
We created a SQL-like front-end to the Azure CLI to create and RBAC roles on the data-plane of Azure CosmosDB accounts.  The purpose was to simplify permissions management by using an interface already familiar to developers/database administrators.

This was done as a python script that calls the Azure CLI.  There are python libraries available for managing Azure Cosmos DB accounts; however, these libraries are for control-plane management (eg, creating accounts, databases, collections) not for managing data-plane activities.  Using the Azure CLI also lets us document the exact CLI commands issued in order to perform the corresponding SQL call.

To call the script we do the following:

`python3 azcosmosdb_perms.py script_file <file_name> [debug (0|1|2|3)] [print_az (0|1)]`
- **script_file <file_name>**: specify name of file holding script
- **debug (0|1|2|3)**: default 0.  Provide additional debugging info
- **print_az (0|1)**: default 0.  Print out corresponding azure cli command.

Additional information on using RBAC to manage access to the data plane of Azure Cosmos DB can be found at:  https://docs.microsoft.com/en-us/azure/cosmos-db/how-to-setup-rbac

## Environment Setup
In Azure, we create the following resources:
- Cosmos DB Account (SQL) named **cosmosdbacct01**
- Database in this account named **WebStore**
- Collections in this database named **Customer**, **Product** and **ProductMeta**

On the client, the following software should be installed:
    - python : this has been tested with python 3.8
    - Azure CLI version 2.24.  Installation instructions can be found at (How to Install the Azure CLI)[https://docs.microsoft.com/en-us/cli/azure/install-azure-cli].  To determine the version you have installed: `az version`

Set up the Azure CLI environment to connect to your account as follows:

- `az login`
   
   This will cache the connection credentials used by calls to Azure CLI.  It will bring up webpage for authentication.  You can use --use-device-code parameter if you want to manually bring up the browser and login to an account
- `az account set -s <subscription_name>`

   This is only needed if you have more than one subscription.

- `az status`

    Show the current connection info so you can confirm you are using the proper connection.


At this point you should be able to call the test scripts provided.  For example:
    `python3 azcosmosdb_perms.py test1.sql`

Note:  This was tested on both Windows 10 and MacOs 11.6

## Testing Method and Results

We ran three different SQL scripts.
- [test1.sql](./test1.sql) : create some roles and grants 
- [test2.sql](./test2.sql) : list/describe info on current environment
- [test3.sql](./test3.sql) : revoke/drop roles created in test1.sql

From each of these scripts we generated the following:
- test#.out [test1](./test1.out), [test2](./test2.out), [test3](./test3.out) : output of the run
- test#_stripped.sql [test1](./test1_stripped.sql), [test2](./test2_stripped.sql), [test3](./test3_stripped.sql): sql script without comments and extra spaces (used for counts of SQL script below)
- test#_az_cmd.txt [test1](./test1_az_cmd.txt), [test2](./test2_az_cmd.txt), [test3](./test3_az_cmd.txt)  : Azure CLI commands to run the corresponding actions (used for count of AZ CLI below)

**Total character counts (from stripped.sql and az_cmd.txt files): **

| Test | SQL # Chars | AZ # Chars |
|-------|-----|------|
| test1 | 545 | 3082 |
| test2 | 213 | 987 |
| test3 | 423 |  1272 |




## SQL Syntax
- [Elements](#elements)
- [USE](#use)
- [CREATE ROLE](#create-role)
- [DESCRIBE ROLE](#describe-role)
- [GRANT ROLE](#grant-role)
- [LIST](#list)
    - COLLECTIONS
    - DATABASES
    - GRANTS
    - ROLES
- [EXITONERROR](#exitonerror)
- [NOEXITONERROR](#noexitonerror)
- [REVOKE ROLE](#revoke-role)


## Elements

`<permissions>`: comma separated list of permissions.


The available permissions are as follows:

- all (custom: all privileges)
- allitem (custom: readmetadata, item*)
- createitem
- execute
- insertitem
- manageconflicts
- query
- readchangefeed
- readitem
- readmetadata
- replaceitem
- select (custom: readmetadata, query, readitem)
- updateitem
- upsertitem

`<cosmosdb_acct>`: name of an existing cosmosdb account in the current subscription

`<database_name>`: name of an existing database

`<role_name>`: name of a role

`<context>`: context for the call.
This can have the following forms:
- <cosmosdb_acct>:  specific cosmosdb account
- <cosmosdb_acct>.<database_name>: specify specific database within a cosmosdb account

`<user>`: User defined in Azure AD


## USE

`USE [<context>]`

Specify the context for subsequent commands.  If not specified, unsets the current context.


## CREATE ROLE
`CREATE ROLE <role_name> WITH <permissions>`

Create a role with the specified permissions.

`CREATE ROLE <role_name> WITH <permissions> ON <context>`

Create a role on a specific context.   When granting the role, it must be done within the specified context.


## DESCRIBE ROLE
`DESCRIBE ROLE <role_name>`

Give context and permission info on defined role.


## DROP ROLE
`DROP ROLE <role_name>`

Drop the specified role.  You can only specify custom roles, not the built-in roles.


## GRANT ROLE

`GRANT ROLE <role_name> TO <user>`

Grant a role to a user over the current context.


`GRANT ROLE <role_name> TO <princi> ON <context>`

Grant a role to a user over the specified context.


## LIST
`LIST COLLECTIONS`

list collections within the current context (account & database should be set with USE command)

`LIST DATABASES`

list of databases within the current CosmosDB account

`LIST GRANTS`

List all role grants within the current CosmosDB account

`LIST ROLES`

List all roles defined in current CosmosDB account


## EXITONERROR
`EXITONERROR`

Exit when an error is encounted.  Note, some non-harmful errors (eg, DESCRIBE) will report as warnings and continue onto next command.

## NOEXITONERROR
`NOEXITONERROR`

Report error but continue to process commands.


## REVOKE ROLE
`REVOKE ROLE <role_name> FROM <user>`

Revoke role from user over the current context

`REVOKE ROLE <role_name> FROM <user> ON <context>`

Revoke role from user over the specified context

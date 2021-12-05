-- set context for subsequent commands
use cosmosdbacct01.WebStore

-- list definitions defined
list roles
list databases
list grants
list collections

-- describe the roles
describe role webstore_support
describe role webstore_itemupdate
describe role webstore_itemadmin
describe role webstore_reporter

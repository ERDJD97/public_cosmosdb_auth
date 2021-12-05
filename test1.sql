-- set context for subsequent commands
use cosmosdbacct01.WebStore

-- create our roles
-- create role for support (read privileges over entire database)
create role webstore_support with select, execute, readchangefeed

-- create role for inserting/updating items only (no delete)
create role webstore_itemupdate with readitem, replaceitem, upsertitem, query

-- create role for item admin (all item privs and readmeta)
create role webstore_itemadmin with allitem

-- create role for reporting
create role webstore_reporter with readmetadata,query,readitem

-- grant roles to support personnel
grant role webstore_support to dev.franklin@edwinrdiazoutlook.onmicrosoft.com

-- grant roles to different parts of the app
grant role webstore_itemupdate to appCustomer@edwinrdiazoutlook.onmicrosoft.com on Customer
grant role webstore_itemadmin to appCustomerAdmin@edwinrdiazoutlook.onmicrosoft.com on Customer
grant role webstore_reporter to appReport@edwinrdiazoutlook.onmicrosoft.com


-- review what was done
list grants

use cosmosdbacct01.WebStore
create role webstore_support with select, execute, readchangefeed
create role webstore_itemupdate with readitem, replaceitem, upsertitem, query
create role webstore_itemadmin with allitem
create role webstore_reporter with readmetadata,query,readitem
grant role webstore_support to dev.franklin@contosa.com
grant role webstore_itemupdate to appCustomer@contosa.com on Customer
grant role webstore_itemadmin to appCustomerAdmin@contosa.com on Customer
grant role webstore_reporter to appReport@contosa.com
list grants

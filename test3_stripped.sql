use cosmosdbacct01.WebStore
NoExitOnError
revoke role webstore_support from dev.franklin@contosa.com
revoke role webstore_itemupdate from appCustomer@contosa.com on Customer
revoke role webstore_itemadmin from appCustomerAdmin@contosa.com on Customer
revoke role webstore_reporter from appReport@contosa.com
drop role webstore_support 
drop role webstore_itemupdate
drop role webstore_itemadmin
drop role webstore_reporter

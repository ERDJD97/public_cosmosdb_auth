use cosmosdbacct01.WebStore

NoExitOnError

-- undo all actions done in test1

revoke role webstore_support from dev.franklin@edwinrdiazoutlook.onmicrosoft.com
revoke role webstore_itemupdate from appCustomer@edwinrdiazoutlook.onmicrosoft.com on Customer
revoke role webstore_itemadmin from appCustomerAdmin@edwinrdiazoutlook.onmicrosoft.com on Customer
revoke role webstore_reporter from appReport@edwinrdiazoutlook.onmicrosoft.com

drop role webstore_support 
drop role webstore_itemupdate
drop role webstore_itemadmin
drop role webstore_reporter


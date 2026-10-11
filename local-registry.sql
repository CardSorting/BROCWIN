-- Derived from scripts/sync-server-ip.ps1. Run only via theseus/isolate.py sql.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
BEGIN TRANSACTION;
UPDATE [Statistics].dbo.LServerList
SET [IP] = N'127.0.0.1', [PrivateIP] = N'127.0.0.1', [PublicIP] = N'127.0.0.1'
WHERE UID IN (1, 2, 3, 4, 6);
IF @@ROWCOUNT <> 5 THROW 50000, 'Expected exactly five native server rows.', 1;
UPDATE [Statistics].dbo.LChannelList SET [IP] = N'127.0.0.1' WHERE OnOff = 1;
IF @@ROWCOUNT < 1 THROW 50000, 'Expected an active native channel.', 1;
COMMIT TRANSACTION;
SELECT UID,IP,PrivateIP,PublicIP FROM [Statistics].dbo.LServerList WHERE UID IN (1,2,3,4,6);

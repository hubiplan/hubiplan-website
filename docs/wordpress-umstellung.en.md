# WordPress migration behind HestiaCP

The automatic `deploy/hestia/umstellen.sh` migration is intended for a conventional
local database managed by the selected Hestia user. It never executes
`wp-config.php` as PHP or shell code. The configuration must be readable and at
most 256 KiB, with exactly one complete literal `define('DB_NAME', '…');` line.
The database name must contain 1–63 ASCII characters, start with a letter or digit,
and otherwise contain only letters, digits, `_` or `-`.

Before creating a backup or changing nginx, the script checks ownership using
`v-list-database HUSER DB_NAME json`. Only its exit status is used; all output is
discarded. Connection details and configuration contents are not logged. The dump
also receives `--` before the database argument, so it cannot become another
command-line option. An unreadable, dynamic, ambiguous, unsupported or foreign
database definition aborts the migration. A failed dump also prevents the nginx
change. Backups remain isolated by user, domain and a unique timestamp directory.

External databases, nonstandard database hosts or unusual configurations require
a separate manual procedure: an administrator must verify the actual database
target and authorization from trusted operational records, use credentials scoped
to that database, create a backup and verify restorability. Back up the existing
files and nginx template for the specific user/domain as well. Only then
deliberately change the domain template in Hestia. Do not delete or rename the
configuration, or bypass the checks, to force the automatic script to proceed.
There is no skip-check override. A safe literal and Hestia ownership do not prove
the complete PHP runtime configuration or external database topology.

References: [Hestia CLI](https://hestiacp.com/docs/reference/cli#v-list-database),
[mysqldump](https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html).

#### Cron Entries###
#---- pyzscale ----
47 08 * * 1-5 /home/qoptrprod/apps/pyzscale/scripts/prod.instrdownloader.sh
10 09 * * 1-5 /home/qoptrprod/apps/pyzscale/scripts/prod.start.md.sh
14 09 * * 1-5 /home/qoptrprod/apps/pyzscale/scripts/prod.start.datarecorder.sh

#-stop scripts
31 15 * * 1-5 /home/qoptrprod/apps/pyzscale/scripts/stop.prod.datarecorder.sh
40 15 * * 1-5 /home/qoptrprod/apps/pyzscale/scripts/stop.prod.md.sh

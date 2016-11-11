#!/bin/bash

#remember chmod 666
uwsgi --ini uwsgi.conf --manage-script-name --mount /=frontseat:app

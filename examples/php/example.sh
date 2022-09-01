#! /usr/bin/env bash
sudo curl -X PUT --data-binary '{
  "listeners": {
      "*:8080": {
          "pass": "applications/php"
      }
  },
  "applications": {
      "php": {
          "type": "php",
          "root": "/www/php"
      }
  }
  }' http://localhost:8080/config/
curl http://localhost:8080

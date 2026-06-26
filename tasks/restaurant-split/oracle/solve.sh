#!/bin/bash
python3 -c "t=186.40; print(round((t + t*0.18 + t*0.0725)/4, 2))" > /root/answer.txt

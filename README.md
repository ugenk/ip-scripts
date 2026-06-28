Scripts to parse lists of IP addresses
======================================

all scripts read data on stdin and producing data on stdout

* `ripe_ncc_extractor.py` - parses data from list like https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest and filters by country and type
* `strip_bogons.py` - filter bogon nets
* `count_ips.py` - counts total number of IPs covered by a list of CIDR networks (use `--unique` to count overlaps once)
* `supernets.py` - aggregates list of IPs, e.g "192.168.0.0/24 192.168.1.0/24" would be aggregated as "192.168.0.0/23"

Example usage:

```bash
cat delegated-ripencc-latest | ripe_ncc_extract.py --ipv4 -c BY > ripe4.txt
cat mylist4.txt ripe4.txt | strip_bogons.py | supernets.py > result4.txt
cat result4.txt | count_ips.py
```
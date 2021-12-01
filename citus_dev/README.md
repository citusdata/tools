# Setup

To install dependencies run:

```bash
pip install -r requirements.txt
```

Add `citus_dev` to your PATH:

```bash
export PATH=$PATH:<your path to citus_dev folder>
```

You can also add this to your profile:

```bash
echo 'export PATH=$PATH:<your path to citus_dev folder>' >>~/.profile
```

After that, you can use the citus dev tool:

```bash
citus_dev make clusterName
```

For the full command list:

```bash
citus_dev --help
```

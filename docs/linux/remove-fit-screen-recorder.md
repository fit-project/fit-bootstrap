# Remove FIT Screen Recorder on Linux

This procedure removes the `fit-screen-recorder` Debian package installed by
FIT. Use it to reset the environment before testing the recorder installation
flow again.

> This procedure applies to Debian, Ubuntu, and derived distributions that use
> `apt` and `dpkg`.

## 1. Inspect the installed package

Check whether the package is installed and display its version:

```bash
dpkg-query -W -f='${Status}\nVersion: ${Version}\n' fit-screen-recorder
```

When the package is installed, the first output line is:

```text
install ok installed
```

You can inspect all files owned by the package before removing it:

```bash
dpkg-query -L fit-screen-recorder
```

## 2. Remove the package

```bash
sudo apt remove fit-screen-recorder
```

Review the package list shown by `apt` before confirming the operation. This
removes the recorder executable while retaining any package configuration that
Debian may track.

To also remove package-managed configuration files, use `purge` instead:

```bash
sudo apt purge fit-screen-recorder
```

Do not run both commands; choose either `remove` or `purge`.

## 3. Verify the removal

The following command must no longer print `install ok installed`. After
`remove`, it may report `deinstall ok config-files`; after `purge`, it normally
reports that the package was not found:

```bash
dpkg-query -W -f='${Status}\n' fit-screen-recorder
```

Also confirm that the executable is no longer available:

```bash
if command -v fit-screen-recorder >/dev/null 2>&1; then
  echo "fit-screen-recorder is still available at: $(command -v fit-screen-recorder)"
else
  echo "FIT Screen Recorder removed"
fi
```

If the executable is still found, inspect the reported path before deleting
anything. It may have been installed manually and may not belong to the Debian
package.

## Optional: remove unused dependencies

After reviewing the packages proposed for removal, dependencies that are no
longer required can be removed with:

```bash
sudo apt autoremove
```

This command may include packages unrelated to FIT, so confirm the displayed
list carefully.

## Run the installation test again

Start FIT normally. It will detect that `fit-screen-recorder` is missing and
offer to install the bundled Debian package again. Administrator authorization
will be requested through PolicyKit before the installation starts.

If `apt` or `dpkg-query` is unavailable, do not use these commands. The current
FIT Screen Recorder installation flow supports only compatible Debian-based
systems.

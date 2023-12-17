# ds6_pc98_trans
An English fan translation of Dragon Slayer: The Legend of Heroes for the PC-98.

Some quick notes on usage follow.

## Building the patch

Open ds6_patch.conf and make sure that the `Original...` fields point to your original .nfd disk images. Also make sure that `NasmPath` points to the nasm executable.

Run `python build_patch.py`. This should produce .ips patches for each disk, as well as a patched copy of each disk, in the "build" subfolder.

## Modifying translations

You can use e.g. `python test_translation.py 10.00.20` to attempt to process a single CSV file and check for errors. (Typically, the errors you'll see are due to the translated text being too long to fit into the original disk sectors.)

Using e.g. `python preview_text.py 10.00.20` will bring up a quick preview display that will let you confirm that the text fits the in-game dialog window correctly. Up/down arrow keys change the current page or selection. Tab navigates from the text window to the flag selection panes; space toggles a flag on and off.

`python import_from_tpp.py` and `python export_to_tpp.py` will allow you to sync the translation CSVs with a Translator++ project. Running the "import" script will generate a file called "ds6.trans" in the current directory. The "export" script will write any changes made in that file back to the CSVs.
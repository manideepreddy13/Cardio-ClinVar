import re

def prefilter():
    # Open files for reading and writing
    with open('./variant_summary.txt', 'r') as clinvar_file, \
         open('./summary_prefiltered', 'w') as out_file, \
         open('./variant_summary.error', 'w') as error_file:

        # Read all lines from input file
        clinvar = clinvar_file.readlines()

        # Filter lines containing 'GRCh37'
        file_lines = [line for line in clinvar if re.search(r'\tGRCh37\t', line)]

        # Write header to output file
        out_file.write("GeneSymbol\tType\tClinicalSignificance\tOriginSimple\tPhenotypeList\tName\tcvid\tkey\ttranscrip\tconsequence\tref_aa\talt_aa\tpos_aa\treview\n")

        # Process each line
        for h, line in enumerate(file_lines):
            # Skip header line
            if h == 0:
                continue

            # Split line into fields
            fields = line.strip().split('\t')

            # Extract relevant fields
            id, type, mut, gene, chr, ini, fin, ref, alt, dis, origin, sig, rev, varid, lastEvaluted = fields[0], fields[1], fields[2], fields[4], fields[18], fields[19], fields[20], fields[21], fields[22], fields[13], fields[14], fields[6], fields[24], fields[30], fields[8]

            # Define default values for extra fields
            consequence, aa_ref, pos_aa, aa_alt, transcript, var, var2 = "NA", "NA", "NA", "NA", "NA", "NA", "NA"

            # Structure of the mutation entry
            if ":" in mut:
                transcript, var = mut.split(":", 1)
                transcript = re.sub(r'\(.*\)', '', transcript)

                # Parsing variant
                if var.startswith("p."):
                    var = var[3:].replace("*", "Ter")
                    aa_ref = var.split("-")[0].split("=")[0]
                    aa_alt = var.split("-")[1] if "-" in var else aa_ref
                    pos_aa = re.sub(r'[a-zA-Z=]+', '', var)

                    if aa_alt == "=":
                        consequence = "Synonymous"
                    elif "fs" in aa_alt:
                        consequence = "Frameshift"
                    elif re.search(r'del|ins|dup', aa_alt):
                        consequence = "In frame indel"
                    elif aa_alt != aa_ref:
                        consequence = "Missense"
                    elif "Ter" in aa_alt:
                        consequence = "Stop gain"
                elif var.startswith("c.-"):
                    consequence = "Start loss" if re.search(r'c.-[0-9]+\+[123][ACTG]', var) else "5-UTR"
                elif var.startswith("c.*"):
                    consequence = "Stop loss" if re.search(r'c.\*[0-9]+-[123][ACTG]', var) else "3-UTR"
                elif var.startswith("c."):
                    consequence = "Splice-D/A" if re.search(r'c.[0-9]+\+[12][ACTG]|c.[0-9]+-[12][ACTG]', var) else "Intronic"
                elif re.search(r'g\..*del|dup', var):
                    consequence = "NA"
                elif re.search(r'g\.', var):
                    consequence = "Genomic"
                    pos_aa = var
                elif var.startswith("n."):
                    consequence = "Non-coding"
                elif var.startswith("m."):
                    consequence = "Mitochondrial"
                elif type.startswith("deletion") or type.startswith("duplication") or type.startswith("complex"):
                    consequence = "NA"
                    pos_aa = var
                else:
                    error_file.write(f"{type}\t{var}\n")

            else:
                error_file.write(f"===>{type}\t{var}\n")

            if "cardiomyopathy" in dis.lower():
                key = f"{chr};{ini};{fin};{ref};{alt}"
                out_file.write(f"{gene}\t{type}\t{sig}\t{origin}\t{dis}\t{mut}\tCV:{id}\t{key}\t{transcript}\t{consequence}\t{aa_ref}\t{aa_alt}\t{pos_aa}\t{rev}\t{varid}\t{lastEvaluted}\n")

if __name__ == "__main__":
    prefilter()

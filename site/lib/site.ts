/** Public repository URL (override with NEXT_PUBLIC_REPO_URL). */
export const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL || "https://github.com/nanos007/grindstone-pq";

export const CONTACT_EMAIL = "georgios.nanos@rwth-aachen.de";

/** Donation address, same as the bitdome project (C:\Projects\bitdome\03_code\components\Nav.tsx). Checksum verified. */
export const BITCOIN_ADDRESS = "14SrrzdeaZ9WotWopNPnxL8z2BJCgds1pn";

/** Path prefix for raw asset URLs (next/link adds it itself; <img>/<a> to public files do not). */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** Built by paper/build_pdf.py from the /paper/ page, so both always match. */
export const PAPER_PDF = "grindstone-paper.pdf";

/** Shown site-wide until the must-fix items in the paper's §7 are closed. */
export const DRAFT = true;

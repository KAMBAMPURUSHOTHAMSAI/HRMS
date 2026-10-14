import { useCallback, useEffect, useRef, useState } from "react";
import {
  Download,
  FileText,
  RefreshCw,
  Search,
  Trash2,
  Upload,
} from "lucide-react";

import {
  deleteEmployeeDocument,
  downloadEmployeeDocument,
  getAllDocuments,
  getMyDocuments,
  uploadEmployeeDocument,
  uploadMyDocument,
} from "../../../api/documentApi";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"];

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || "Invalid input")
      .join(", ");
  }

  return error?.message || fallback;
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 10);
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatFileSize(size) {
  const bytes = Number(size || 0);

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function safeFilename(value) {
  const filename = String(value || "employee-document")
    .replace(/[\\/:*?"<>|\r\n]/g, "_")
    .trim();

  return filename || "employee-document";
}

function filenameFromDisposition(disposition, fallback) {
  if (!disposition) {
    return safeFilename(fallback);
  }

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    try {
      return safeFilename(decodeURIComponent(utf8Match[1].replace(/"/g, "")));
    } catch {
      // Fall back to the ordinary filename below.
    }
  }

  const match = disposition.match(/filename="?([^";]+)"?/i);

  return safeFilename(match?.[1] || fallback);
}

async function getDownloadErrorMessage(error, fallback) {
  const responseData = error?.response?.data;

  if (responseData instanceof Blob) {
    try {
      const parsed = JSON.parse(await responseData.text());

      if (typeof parsed.detail === "string") {
        return parsed.detail;
      }
    } catch {
      // Ignore non-JSON error responses.
    }
  }

  return getErrorMessage(error, fallback);
}

export default function EmployeeDocuments({ mode = "employee" }) {
  const isAdminPage = mode === "admin";
  const fileInputRef = useRef(null);

  const [documents, setDocuments] = useState([]);

  const [employeeId, setEmployeeId] = useState("");
  const [appliedEmployeeId, setAppliedEmployeeId] = useState("");

  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("OTHER");
  const [description, setDescription] = useState("");

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [activeDocumentId, setActiveDocumentId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      let result;

      if (isAdminPage) {
        const params = appliedEmployeeId
          ? { employee_id: Number(appliedEmployeeId) }
          : {};

        result = await getAllDocuments(params);
      } else {
        result = await getMyDocuments();
      }

      setDocuments(Array.isArray(result) ? result : []);
    } catch (err) {
      setDocuments([]);
      setError(
        getErrorMessage(err, "Unable to load employee documents.")
      );
    } finally {
      setLoading(false);
    }
  }, [isAdminPage, appliedEmployeeId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  function validateSelectedFile(selectedFile) {
    if (!selectedFile) {
      setError("Please select a document to upload.");
      return false;
    }

    const filename = selectedFile.name.toLowerCase();

    const isAllowed = ALLOWED_EXTENSIONS.some((extension) =>
      filename.endsWith(extension)
    );

    if (!isAllowed) {
      setError("Only PDF, PNG, JPG, and JPEG files are accepted.");
      return false;
    }

    if (selectedFile.size <= 0) {
      setError("The selected file is empty.");
      return false;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError("File size cannot exceed 5 MB.");
      return false;
    }

    return true;
  }

  async function handleUpload(event) {
    event.preventDefault();

    setError("");
    setMessage("");

    if (!validateSelectedFile(file)) {
      return;
    }

    if (isAdminPage) {
      const numericEmployeeId = Number(employeeId);

      if (
        !employeeId ||
        !Number.isInteger(numericEmployeeId) ||
        numericEmployeeId <= 0
      ) {
        setError("Enter a valid employee ID for the upload.");
        return;
      }
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("document_type", documentType);
    formData.append("description", description.trim());

    setUploading(true);

    try {
      if (isAdminPage) {
        await uploadEmployeeDocument(Number(employeeId), formData);
      } else {
        await uploadMyDocument(formData);
      }

      setMessage("Document uploaded successfully.");

      setFile(null);
      setDocumentType("OTHER");
      setDescription("");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadDocuments();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to upload the document.")
      );
    } finally {
      setUploading(false);
    }
  }

  // Corrected: use `item` instead of `document` to avoid
  // shadowing the browser's global document object.
  async function handleDownload(item) {
    setActiveDocumentId(item.id);
    setError("");
    setMessage("");

    let objectUrl;

    try {
      const result = await downloadEmployeeDocument(item.id);

      if (!(result.blob instanceof Blob) || result.blob.size === 0) {
        throw new Error("The downloaded file is empty.");
      }

      objectUrl = URL.createObjectURL(result.blob);

      const filename = filenameFromDisposition(
        result.contentDisposition,
        item.original_filename
      );

      const link = window.document.createElement("a");

      link.href = objectUrl;
      link.download = filename;

      window.document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage(`Download requested for ${filename}.`);
    } catch (err) {
      setError(
        await getDownloadErrorMessage(
          err,
          "Unable to download this document."
        )
      );
    } finally {
      if (objectUrl) {
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      }

      setActiveDocumentId(null);
    }
  }

  async function handleDelete(item) {
    const confirmed = window.confirm(
      `Delete document "${item.original_filename}"?`
    );

    if (!confirmed) return;

    setActiveDocumentId(item.id);
    setError("");
    setMessage("");

    try {
      await deleteEmployeeDocument(item.id);

      setMessage("Document deleted successfully.");
      await loadDocuments();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to delete this document.")
      );
    } finally {
      setActiveDocumentId(null);
    }
  }

  function applyEmployeeFilter(event) {
    event.preventDefault();

    if (
      employeeId &&
      (!Number.isInteger(Number(employeeId)) ||
        Number(employeeId) <= 0)
    ) {
      setError("Employee ID must be a positive integer.");
      return;
    }

    setError("");
    setAppliedEmployeeId(employeeId.trim());
  }

  function clearEmployeeFilter() {
    setEmployeeId("");
    setAppliedEmployeeId("");
    setError("");
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">
            {isAdminPage ? "Employee Documents" : "My Documents"}
          </h2>

          <p className="text-muted mb-0">
            {isAdminPage
              ? "Manage employee documents and access controlled files."
              : "Upload and manage your personal HR documents."}
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadDocuments}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {message && <div className="alert alert-success">{message}</div>}

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">
            <Upload size={20} className="me-2" />
            Upload Document
          </h5>

          <form className="row g-3" onSubmit={handleUpload}>
            {isAdminPage && (
              <div className="col-md-3">
                <label className="form-label">Employee ID *</label>

                <input
                  type="number"
                  min="1"
                  className="form-control"
                  value={employeeId}
                  onChange={(event) => setEmployeeId(event.target.value)}
                  placeholder="Enter employee ID"
                  required
                />
              </div>
            )}

            <div className={isAdminPage ? "col-md-3" : "col-md-4"}>
              <label className="form-label">Document Type *</label>

              <select
                className="form-select"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
                required
              >
                <option value="ID_PROOF">ID Proof</option>
                <option value="CONTRACT">Contract</option>
                <option value="CERTIFICATE">Certificate</option>
                <option value="RESUME">Resume</option>
                <option value="OTHER">Other</option>
              </select>
            </div>

            <div className={isAdminPage ? "col-md-6" : "col-md-8"}>
              <label className="form-label">Choose File *</label>

              <input
                ref={fileInputRef}
                type="file"
                className="form-control"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  setError("");
                }}
                required
              />

              <small className="text-muted">
                PDF, PNG, JPG, JPEG. Maximum 5 MB.
              </small>
            </div>

            <div className="col-12">
              <label className="form-label">Description</label>

              <textarea
                className="form-control"
                rows={2}
                maxLength={1000}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional description"
              />
            </div>

            <div className="col-12">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={uploading}
              >
                <Upload size={16} className="me-2" />
                {uploading ? "Uploading..." : "Upload Document"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {isAdminPage && (
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">Filter by Employee</h5>

            <form
              className="row g-3"
              onSubmit={applyEmployeeFilter}
            >
              <div className="col-md-5">
                <label className="form-label">Employee ID</label>

                <input
                  type="number"
                  min="1"
                  className="form-control"
                  value={employeeId}
                  onChange={(event) => setEmployeeId(event.target.value)}
                  placeholder="Leave empty to view all employees"
                />
              </div>

              <div className="col-md-7 d-flex align-items-end gap-2">
                <button type="submit" className="btn btn-primary">
                  <Search size={16} className="me-1" />
                  Apply Filter
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={clearEmployeeFilter}
                >
                  Clear Filter
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">
            Document List ({documents.length})
          </h5>

          {loading ? (
            <p>Loading documents...</p>
          ) : documents.length === 0 ? (
            <div className="text-center py-5">
              <FileText size={36} className="text-muted mb-2" />
              <h6>No documents found</h6>
              <p className="text-muted mb-0">
                Uploaded documents will appear here.
              </p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Document</th>
                    {isAdminPage && <th>Employee</th>}
                    <th>Type</th>
                    <th>Size</th>
                    <th>Description</th>
                    <th>Uploaded At</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {documents.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <FileText
                          size={17}
                          className="me-2 text-primary"
                        />
                        {item.original_filename}
                      </td>

                      {isAdminPage && (
                        <td>
                          <div className="fw-semibold">
                            {item.employee_name || "—"}
                          </div>

                          <small className="text-muted">
                            {item.employee_code ||
                              `ID ${item.employee_id}`}
                          </small>

                          <br />

                          <small className="text-muted">
                            {item.employee_email || ""}
                          </small>
                        </td>
                      )}

                      <td>{item.document_type}</td>
                      <td>{formatFileSize(item.file_size)}</td>
                      <td>{item.description || "—"}</td>
                      <td>{formatDate(item.created_at)}</td>

                      <td>
                        <div className="d-flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => handleDownload(item)}
                            disabled={activeDocumentId === item.id}
                          >
                            <Download size={14} className="me-1" />
                            Download
                          </button>

                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => handleDelete(item)}
                            disabled={activeDocumentId === item.id}
                            aria-label={`Delete ${item.original_filename}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-muted small mt-3 mb-0">
            Document downloads require authentication and authorization.
          </p>
        </div>
      </div>
    </section>
  );
}
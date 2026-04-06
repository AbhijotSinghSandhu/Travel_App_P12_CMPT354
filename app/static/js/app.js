const { useEffect, useState } = React;

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "same-origin",
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function App() {
  const emptyBootstrap = {
    places: [],
    categories: [],
    public_lists: [],
    admin_overview: null,
    filters: { search: "", category: "" },
    user: null,
  };

  const [bootstrap, setBootstrap] = useState(emptyBootstrap);
  const [session, setSession] = useState(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState(null);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [ownLists, setOwnLists] = useState([]);
  const [selectedOwnList, setSelectedOwnList] = useState(null);
  const [selectedPublicList, setSelectedPublicList] = useState(null);
  const [filters, setFilters] = useState({ search: "", category: "" });
  const [authMode, setAuthMode] = useState("login");
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authForm, setAuthForm] = useState({
    username: "",
    email: "",
    display_name: "",
    password: "",
    role: "tourist",
  });
  const [reviewForm, setReviewForm] = useState({ rating: "5", title: "", body: "" });
  const [editingReviewId, setEditingReviewId] = useState(null);
  const [listForm, setListForm] = useState({ title: "", description: "", is_public: true });
  const [listEditForm, setListEditForm] = useState({ title: "", description: "", is_public: true });
  const [addToListForm, setAddToListForm] = useState({ list_id: "", note: "" });
  const [claimForm, setClaimForm] = useState({ message: "" });
  const [photoForm, setPhotoForm] = useState({ photo_url: "", caption: "" });
  const [placeForm, setPlaceForm] = useState({
    name: "",
    address: "",
    description: "",
    hours: "",
    contact_info: "",
    website: "",
    category_ids: [],
  });
  const [newPlaceForm, setNewPlaceForm] = useState({
    name: "",
    address: "",
    description: "",
    hours: "",
    contact_info: "",
    website: "",
    category_ids: [],
  });

  useEffect(() => {
    initialize();
  }, []);

  useEffect(() => {
    if (selectedPlaceId) {
      loadPlaceDetail(selectedPlaceId);
    } else {
      setSelectedPlace(null);
    }
  }, [selectedPlaceId]);

  useEffect(() => {
    if (selectedOwnList) {
      setListEditForm({
        title: selectedOwnList.list.Title || "",
        description: selectedOwnList.list.Description || "",
        is_public: Boolean(selectedOwnList.list.IsPublic),
      });
    }
  }, [selectedOwnList]);

  function flash(type, text) {
    setMessage({ type, text });
  }

  async function initialize() {
    setLoading(true);
    try {
      await refreshDashboard();
    } catch (error) {
      flash("error", error.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshDashboard(nextFilters = filters, preferredPlaceId = selectedPlaceId) {
    const query = new URLSearchParams();
    if (nextFilters.search) query.set("search", nextFilters.search);
    if (nextFilters.category) query.set("category", nextFilters.category);

    const data = await apiFetch(`/api/bootstrap${query.toString() ? `?${query.toString()}` : ""}`);
    setBootstrap(data);
    setSession(data.user);

    const matchingPlaceIds = data.places.map((place) => place.PlaceID);
    const nextPlaceId = matchingPlaceIds.includes(preferredPlaceId)
      ? preferredPlaceId
      : data.places[0]?.PlaceID || null;
    setSelectedPlaceId(nextPlaceId);

    if (data.user) {
      await loadOwnLists();
    } else {
      setOwnLists([]);
      setSelectedOwnList(null);
    }
  }

  async function loadPlaceDetail(placeId) {
    const data = await apiFetch(`/api/places/${placeId}`);
    setSelectedPlace(data);
    setPlaceForm({
      name: data.place.Name || "",
      address: data.place.Address || "",
      description: data.place.Description || "",
      hours: data.place.Hours || "",
      contact_info: data.place.ContactInfo || "",
      website: data.place.Website || "",
      category_ids: data.categories.map((category) => String(category.CategoryID)),
    });
    if (data.user_trip_lists.length && !addToListForm.list_id) {
      setAddToListForm((current) => ({ ...current, list_id: String(data.user_trip_lists[0].ListID) }));
    }
  }

  async function loadOwnLists(openListId = null) {
    const listIndex = await apiFetch("/api/lists");
    setOwnLists(listIndex.lists);
    const targetId = openListId || selectedOwnList?.list?.ListID || listIndex.lists[0]?.ListID;
    if (targetId) {
      const detail = await apiFetch(`/api/lists/${targetId}`);
      setSelectedOwnList(detail);
    } else {
      setSelectedOwnList(null);
    }
  }

  async function openPublicList(listId) {
    try {
      const detail = await apiFetch(`/api/lists/${listId}`);
      setSelectedPublicList(detail);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    try {
      if (authMode === "register") {
        const payload = { ...authForm };
        await apiFetch("/api/register", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setAuthMode("login");
        setAuthForm({ username: "", email: "", display_name: "", password: "", role: "tourist" });
        flash("success", "Registration complete. You can log in now.");
        return;
      }

      const loginData = await apiFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({ email: authForm.email, password: authForm.password }),
      });
      setSession(loginData.user);
      setAuthForm({ username: "", email: "", display_name: "", password: "", role: "tourist" });
      flash("success", "Login successful.");
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function handleLogout() {
    try {
      await apiFetch("/api/logout", { method: "POST" });
      setSession(null);
      setSelectedOwnList(null);
      setOwnLists([]);
      setSelectedPublicList(null);
      setEditingReviewId(null);
      setReviewForm({ rating: "5", title: "", body: "" });
      setPhotoForm({ photo_url: "", caption: "" });
      setClaimForm({ message: "" });
      flash("success", "You have been logged out.");
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    if (!selectedPlaceId) return;

    try {
      if (editingReviewId) {
        await apiFetch(`/api/reviews/${editingReviewId}`, {
          method: "PUT",
          body: JSON.stringify(reviewForm),
        });
        flash("success", "Review updated successfully.");
      } else {
        await apiFetch(`/api/places/${selectedPlaceId}/reviews`, {
          method: "POST",
          body: JSON.stringify(reviewForm),
        });
        flash("success", "Review posted.");
      }

      setEditingReviewId(null);
      setReviewForm({ rating: "5", title: "", body: "" });
      await refreshDashboard(filters, selectedPlaceId);
      await loadPlaceDetail(selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  function beginEditReview(review) {
    setEditingReviewId(review.ReviewID);
    setReviewForm({
      rating: String(review.Rating),
      title: review.Title || "",
      body: review.Body || "",
    });
  }

  async function deleteReview(reviewId) {
    try {
      await apiFetch(`/api/reviews/${reviewId}`, { method: "DELETE" });
      flash("success", "Review deleted.");
      setEditingReviewId(null);
      setReviewForm({ rating: "5", title: "", body: "" });
      await refreshDashboard(filters, selectedPlaceId);
      await loadPlaceDetail(selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function createList(event) {
    event.preventDefault();
    try {
      const response = await apiFetch("/api/lists", {
        method: "POST",
        body: JSON.stringify(listForm),
      });
      setListForm({ title: "", description: "", is_public: true });
      flash("success", "Trip list created.");
      await loadOwnLists(response.list_id);
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function updateList(event) {
    event.preventDefault();
    if (!selectedOwnList) return;

    try {
      await apiFetch(`/api/lists/${selectedOwnList.list.ListID}`, {
        method: "PUT",
        body: JSON.stringify(listEditForm),
      });
      flash("success", "Trip list updated.");
      await loadOwnLists(selectedOwnList.list.ListID);
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function deleteList() {
    if (!selectedOwnList) return;

    try {
      await apiFetch(`/api/lists/${selectedOwnList.list.ListID}`, { method: "DELETE" });
      flash("success", "Trip list deleted.");
      await loadOwnLists();
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function addPlaceToList(event) {
    event.preventDefault();
    if (!selectedPlaceId) return;

    try {
      await apiFetch(`/api/places/${selectedPlaceId}/lists`, {
        method: "POST",
        body: JSON.stringify(addToListForm),
      });
      setAddToListForm((current) => ({ ...current, note: "" }));
      flash("success", "Place added to trip list.");
      await loadOwnLists(addToListForm.list_id);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function removeFromList(listId, placeId) {
    try {
      await apiFetch(`/api/lists/${listId}/places/${placeId}`, { method: "DELETE" });
      flash("success", "Place removed from list.");
      await loadOwnLists(listId);
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function moveListItem(direction, index) {
    if (!selectedOwnList) return;

    const items = [...selectedOwnList.items];
    const swapIndex = direction === "up" ? index - 1 : index + 1;
    if (swapIndex < 0 || swapIndex >= items.length) return;

    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
    const orderedPlaceIds = items.map((item) => item.PlaceID);

    try {
      await apiFetch(`/api/lists/${selectedOwnList.list.ListID}/reorder`, {
        method: "PUT",
        body: JSON.stringify({ ordered_place_ids: orderedPlaceIds }),
      });
      flash("success", "Trip list order updated.");
      await loadOwnLists(selectedOwnList.list.ListID);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function submitClaimRequest(event) {
    event.preventDefault();
    if (!selectedPlaceId) return;

    try {
      await apiFetch(`/api/places/${selectedPlaceId}/claim-requests`, {
        method: "POST",
        body: JSON.stringify(claimForm),
      });
      setClaimForm({ message: "" });
      flash("success", "Claim request submitted.");
      await loadPlaceDetail(selectedPlaceId);
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function submitPhoto(event) {
    event.preventDefault();
    if (!selectedPlaceId) return;

    try {
      await apiFetch(`/api/places/${selectedPlaceId}/photos`, {
        method: "POST",
        body: JSON.stringify(photoForm),
      });
      setPhotoForm({ photo_url: "", caption: "" });
      flash("success", "Photo submitted for moderation.");
      await loadPlaceDetail(selectedPlaceId);
      await refreshDashboard(filters, selectedPlaceId);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function submitManagedPlace(event) {
    event.preventDefault();
    if (!selectedPlace?.permissions?.can_manage_place) return;

    try {
      await apiFetch(`/api/places/${selectedPlace.place.PlaceID}`, {
        method: "PUT",
        body: JSON.stringify(placeForm),
      });
      flash("success", "Place updated.");
      await refreshDashboard(filters, selectedPlace.place.PlaceID);
      await loadPlaceDetail(selectedPlace.place.PlaceID);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function submitNewPlace(event) {
    event.preventDefault();

    try {
      const response = await apiFetch("/api/places", {
        method: "POST",
        body: JSON.stringify(newPlaceForm),
      });
      flash("success", "Place created.");
      setNewPlaceForm({
        name: "",
        address: "",
        description: "",
        hours: "",
        contact_info: "",
        website: "",
        category_ids: [],
      });
      setSelectedPlaceId(response.place_id);
      await refreshDashboard(filters, response.place_id);
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function moderateClaim(claimId, status) {
    try {
      await apiFetch(`/api/admin/claim-requests/${claimId}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      flash("success", `Claim ${status}.`);
      await refreshDashboard(filters, selectedPlaceId);
      if (selectedPlaceId) {
        await loadPlaceDetail(selectedPlaceId);
      }
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function moderatePhoto(photoId, status) {
    try {
      await apiFetch(`/api/admin/photos/${photoId}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      flash("success", `Photo ${status}.`);
      await refreshDashboard(filters, selectedPlaceId);
      if (selectedPlaceId) {
        await loadPlaceDetail(selectedPlaceId);
      }
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function moderateReview(reviewId, isVisible) {
    try {
      await apiFetch(`/api/admin/reviews/${reviewId}`, {
        method: "PUT",
        body: JSON.stringify({ is_visible: isVisible }),
      });
      flash("success", `Review ${isVisible ? "shown" : "hidden"}.`);
      await refreshDashboard(filters, selectedPlaceId);
      if (selectedPlaceId) {
        await loadPlaceDetail(selectedPlaceId);
      }
    } catch (error) {
      flash("error", error.message);
    }
  }

  async function moderatePlace(placeId, isActive) {
    try {
      await apiFetch(`/api/admin/places/${placeId}/status`, {
        method: "PUT",
        body: JSON.stringify({ is_active: isActive }),
      });
      flash("success", `Listing ${isActive ? "restored" : "hidden"}.`);
      await refreshDashboard(filters, selectedPlaceId);
      if (selectedPlaceId) {
        await loadPlaceDetail(selectedPlaceId);
      }
    } catch (error) {
      flash("error", error.message);
    }
  }

  const currentUserReview = selectedPlace?.reviews?.find((review) => review.UserID === session?.user_id);
  const canCreatePlace = session?.role === "business_owner" || session?.role === "admin";

  if (loading) {
    return <div className="shell"><div className="panel">Loading travel planner...</div></div>;
  }

  return (
    <div className="shell">
      <section className="hero">
        <div className="hero-card hero-copy">
          <span className="eyebrow">TripAdvisor-inspired Vancouver planner</span>
          <h1>Discover places, curate itineraries, and moderate community content.</h1>
          <p>
            Travelers can browse and review destinations, save plans into trip lists, and upload photos.
            Business owners can claim listings and keep details current. Admins can moderate claims,
            reviews, photos, and listing visibility from the same app.
          </p>
          <div className="hero-metrics">
            <div className="metric"><strong>{bootstrap.places.length}</strong><span className="subtle">places</span></div>
            <div className="metric"><strong>{bootstrap.public_lists.length}</strong><span className="subtle">public trip lists</span></div>
            <div className="metric"><strong>{selectedPlace?.photos?.length || 0}</strong><span className="subtle">photos here</span></div>
          </div>
        </div>
        <div className="hero-card hero-side">
          <div>
            <div className="status-pill">Flask + React + MySQL</div>
            <h2 className="section-title" style={{ marginTop: 18 }}>Demo accounts</h2>
            <p><strong>Traveler</strong><br />samuel14@example.com / password123</p>
            <p><strong>Business owner</strong><br />owenwang@example.com / owner123</p>
            <p><strong>Admin</strong><br />admin01@example.com / admin123</p>
          </div>
          <div className="subtle">
            Business owners can claim places and manage approved listings. Admins can approve or reject community submissions.
          </div>
        </div>
      </section>

      <div className="top-nav">
        <div>
          <h2 className="section-title">Explore Vancouver</h2>
        </div>
        <div className="nav-actions">
          {session ? (
            <>
              <span className="chip">{session.display_name} · {session.role.replace("_", " ")}</span>
              <button className="ghost" onClick={handleLogout}>Log out</button>
            </>
          ) : (
            <span className="chip">Guest mode</span>
          )}
        </div>
      </div>

      {message && (
        <div className={`notice ${message.type === "error" ? "error" : ""}`} style={{ marginBottom: 20 }}>
          {message.text}
        </div>
      )}

      <section className="toolbar">
        <input
          value={filters.search}
          onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
          placeholder="Search places by name"
        />
        <select
          value={filters.category}
          onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
        >
          <option value="">All categories</option>
          {bootstrap.categories.map((category) => (
            <option key={category.CategoryID} value={category.TagName}>{category.TagName}</option>
          ))}
        </select>
        <button className="ghost" onClick={() => setFilters({ search: "", category: "" })}>Clear filters</button>
        <button className="action" onClick={() => refreshDashboard(filters, selectedPlaceId)}>Refresh</button>
      </section>

      <section className="grid">
        <div className="stack">
          <div className="panel">
            <div className="row-between" style={{ marginBottom: 16 }}>
              <h2 className="section-title">Places</h2>
              <span className="subtle">{bootstrap.places.length} results</span>
            </div>
            <div className="stack">
              {bootstrap.places.map((place) => (
                <div className="place-card" key={place.PlaceID}>
                  <div className="place-header">
                    <div>
                      <h3 style={{ margin: "0 0 8px" }}>{place.Name}</h3>
                      <div className="subtle">{place.Address}</div>
                    </div>
                    <div className="badge-row">
                      {!place.IsActive && <span className="chip">Hidden</span>}
                      {place.ClaimedByUserID && <span className="chip">Claimed</span>}
                      <span className="chip">{place.AvgRating || 0} / 5</span>
                    </div>
                  </div>
                  <p className="subtle">{place.Description || "No description yet."}</p>
                  <button className="card-link" onClick={() => setSelectedPlaceId(place.PlaceID)}>Open details</button>
                </div>
              ))}
              {bootstrap.places.length === 0 && <div className="empty">No places matched your filters.</div>}
            </div>
          </div>

          <div className="panel">
            <div className="row-between" style={{ marginBottom: 12 }}>
              <h2 className="section-title">Public trip lists</h2>
              <span className="subtle">Community itineraries</span>
            </div>
            <div className="stack">
              {bootstrap.public_lists.map((tripList) => (
                <button className="place-card" key={tripList.ListID} onClick={() => openPublicList(tripList.ListID)}>
                  <div className="row-between">
                    <strong>{tripList.Title}</strong>
                    <span className="chip">{tripList.ItemCount} stops</span>
                  </div>
                  <div className="subtle">{tripList.Description || "No description yet."}</div>
                  <div className="subtle">by {tripList.DisplayName}</div>
                </button>
              ))}
              {bootstrap.public_lists.length === 0 && <div className="empty">No public trip lists yet.</div>}
            </div>

            {selectedPublicList && (
              <div className="list-item" style={{ marginTop: 18 }}>
                <h3 style={{ marginTop: 0 }}>{selectedPublicList.list.Title}</h3>
                <p className="subtle">{selectedPublicList.list.Description || "No description yet."}</p>
                <div className="stack">
                  {selectedPublicList.items.map((item) => (
                    <div key={`${item.ListID}-${item.PlaceID}`} className="list-item">
                      <strong>{item.Position}. {item.Name}</strong>
                      <div className="subtle">{item.Address}</div>
                      <div className="subtle">{item.Note || "No note added."}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="panel featured">
            {selectedPlace ? (
              <>
                <div className="row-between">
                  <div>
                    <h2 className="section-title detail-title">{selectedPlace.place.Name}</h2>
                    <p className="subtle">{selectedPlace.place.Address}</p>
                  </div>
                  <div className="badge-row">
                    {!selectedPlace.place.IsActive && <span className="chip">Hidden listing</span>}
                    {selectedPlace.place.ClaimedByName && <span className="chip">Claimed by {selectedPlace.place.ClaimedByName}</span>}
                    <span className="chip">{selectedPlace.place.AvgRating || 0} average</span>
                  </div>
                </div>

                <p>{selectedPlace.place.Description || "No description available yet."}</p>
                <div className="chips">
                  {selectedPlace.categories.map((category) => (
                    <span className="chip" key={category.CategoryID}>{category.TagName}</span>
                  ))}
                </div>

                <div className="mini-grid" style={{ marginTop: 18 }}>
                  <div className="list-item">
                    <strong>Hours</strong>
                    <div className="subtle">{selectedPlace.place.Hours || "Not listed"}</div>
                  </div>
                  <div className="list-item">
                    <strong>Contact</strong>
                    <div className="subtle">{selectedPlace.place.ContactInfo || "Not listed"}</div>
                  </div>
                  <div className="list-item">
                    <strong>Website</strong>
                    <div className="subtle">
                      {selectedPlace.place.Website
                        ? <a href={selectedPlace.place.Website} target="_blank" rel="noreferrer">{selectedPlace.place.Website}</a>
                        : "Not listed"}
                    </div>
                  </div>
                </div>

                <div className="section-block">
                  <h3 style={{ marginTop: 0 }}>Photos</h3>
                  <div className="photo-grid">
                    {selectedPlace.photos.map((photo) => (
                      <div className="photo-card" key={photo.PhotoID}>
                        <img src={photo.PhotoURL} alt={photo.Caption || selectedPlace.place.Name} />
                        <div>
                          <strong>{photo.Caption || "Community photo"}</strong>
                          <div className="subtle">by {photo.DisplayName}</div>
                          {session?.role === "admin" && <div className="subtle">Status: {photo.Status}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                  {selectedPlace.photos.length === 0 && <div className="empty">No approved photos yet.</div>}
                </div>

                {session && (
                  <div className="section-block">
                    <form className="form-grid" onSubmit={submitPhoto}>
                      <h3 style={{ marginBottom: 0 }}>Submit a photo</h3>
                      <div className="field">
                        <input
                          value={photoForm.photo_url}
                          onChange={(event) => setPhotoForm((current) => ({ ...current, photo_url: event.target.value }))}
                          placeholder="https://example.com/photo.jpg"
                        />
                      </div>
                      <div className="field">
                        <input
                          value={photoForm.caption}
                          onChange={(event) => setPhotoForm((current) => ({ ...current, caption: event.target.value }))}
                          placeholder="Short caption"
                        />
                      </div>
                      <button className="ghost" type="submit">Submit for moderation</button>
                    </form>
                  </div>
                )}

                {session && (
                  <div className="section-block">
                    <form className="form-grid" onSubmit={addPlaceToList}>
                      <h3 style={{ marginBottom: 0 }}>Add to your trip list</h3>
                      <div className="field">
                        <select
                          value={addToListForm.list_id}
                          onChange={(event) => setAddToListForm((current) => ({ ...current, list_id: event.target.value }))}
                        >
                          <option value="">Choose a list</option>
                          {selectedPlace.user_trip_lists.map((tripList) => (
                            <option key={tripList.ListID} value={tripList.ListID}>{tripList.Title}</option>
                          ))}
                        </select>
                      </div>
                      <div className="field">
                        <textarea
                          value={addToListForm.note}
                          onChange={(event) => setAddToListForm((current) => ({ ...current, note: event.target.value }))}
                          placeholder="Optional planning note"
                        />
                      </div>
                      <button className="action" type="submit">Save place</button>
                    </form>
                  </div>
                )}

                {session?.role === "business_owner" &&
                  selectedPlace.permissions.can_claim_place &&
                  (!selectedPlace.claim_request || selectedPlace.claim_request.Status === "rejected") && (
                  <div className="section-block">
                    <form className="form-grid" onSubmit={submitClaimRequest}>
                      <h3 style={{ marginBottom: 0 }}>Request to claim this listing</h3>
                      <div className="field">
                        <textarea
                          value={claimForm.message}
                          onChange={(event) => setClaimForm({ message: event.target.value })}
                          placeholder="Tell the admin why you should manage this listing"
                        />
                      </div>
                      <button className="ghost" type="submit">Send claim request</button>
                    </form>
                  </div>
                )}

                {selectedPlace.claim_request && (
                  <div className="notice">
                    Your latest claim request status for this listing: <strong>{selectedPlace.claim_request.Status}</strong>
                  </div>
                )}

                {selectedPlace.permissions.can_manage_place && (
                  <div className="section-block">
                    <form className="form-grid" onSubmit={submitManagedPlace}>
                      <h3 style={{ marginBottom: 0 }}>Update business information</h3>
                      <div className="field">
                        <input value={placeForm.name} onChange={(event) => setPlaceForm((current) => ({ ...current, name: event.target.value }))} placeholder="Place name" />
                      </div>
                      <div className="field">
                        <input value={placeForm.address} onChange={(event) => setPlaceForm((current) => ({ ...current, address: event.target.value }))} placeholder="Address" />
                      </div>
                      <div className="field">
                        <textarea value={placeForm.description} onChange={(event) => setPlaceForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
                      </div>
                      <div className="field">
                        <input value={placeForm.hours} onChange={(event) => setPlaceForm((current) => ({ ...current, hours: event.target.value }))} placeholder="Hours" />
                      </div>
                      <div className="field">
                        <input value={placeForm.contact_info} onChange={(event) => setPlaceForm((current) => ({ ...current, contact_info: event.target.value }))} placeholder="Contact info" />
                      </div>
                      <div className="field">
                        <input value={placeForm.website} onChange={(event) => setPlaceForm((current) => ({ ...current, website: event.target.value }))} placeholder="Website URL" />
                      </div>
                      <div className="field">
                        <label>Categories</label>
                        <select
                          multiple
                          value={placeForm.category_ids}
                          onChange={(event) => setPlaceForm((current) => ({
                            ...current,
                            category_ids: Array.from(event.target.selectedOptions, (option) => option.value),
                          }))}
                        >
                          {selectedPlace.all_categories.map((category) => (
                            <option key={category.CategoryID} value={category.CategoryID}>{category.TagName}</option>
                          ))}
                        </select>
                      </div>
                      <button className="action" type="submit">Save place changes</button>
                    </form>
                  </div>
                )}
              </>
            ) : (
              <div className="empty">Pick a place to see details.</div>
            )}
          </div>

          <div className="panel">
            <div className="row-between" style={{ marginBottom: 12 }}>
              <h2 className="section-title">Account</h2>
              {!session && (
                <button className="auth-switch" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>
                  Switch to {authMode === "login" ? "register" : "login"}
                </button>
              )}
            </div>

            {session ? (
              <div className="stack">
                <div className="notice">
                  Signed in as <strong>{session.display_name}</strong>. Your role is <strong>{session.role.replace("_", " ")}</strong>.
                </div>

                <form className="form-grid" onSubmit={createList}>
                  <h3 style={{ marginBottom: 0 }}>Create a trip list</h3>
                  <div className="field">
                    <input value={listForm.title} onChange={(event) => setListForm((current) => ({ ...current, title: event.target.value }))} placeholder="Weekend food trail" />
                  </div>
                  <div className="field">
                    <textarea value={listForm.description} onChange={(event) => setListForm((current) => ({ ...current, description: event.target.value }))} placeholder="What is this itinerary for?" />
                  </div>
                  <label className="subtle">
                    <input type="checkbox" checked={listForm.is_public} onChange={(event) => setListForm((current) => ({ ...current, is_public: event.target.checked }))} />{" "}
                    Make this public
                  </label>
                  <button className="action" type="submit">Create list</button>
                </form>

                {canCreatePlace && (
                  <div className="section-block">
                    <form className="form-grid" onSubmit={submitNewPlace}>
                      <h3 style={{ marginTop: 0, marginBottom: 0 }}>Create a new place listing</h3>
                      <div className="field">
                        <input value={newPlaceForm.name} onChange={(event) => setNewPlaceForm((current) => ({ ...current, name: event.target.value }))} placeholder="Place name" />
                      </div>
                      <div className="field">
                        <input value={newPlaceForm.address} onChange={(event) => setNewPlaceForm((current) => ({ ...current, address: event.target.value }))} placeholder="Address" />
                      </div>
                      <div className="field">
                        <textarea value={newPlaceForm.description} onChange={(event) => setNewPlaceForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
                      </div>
                      <div className="field">
                        <input value={newPlaceForm.hours} onChange={(event) => setNewPlaceForm((current) => ({ ...current, hours: event.target.value }))} placeholder="Hours" />
                      </div>
                      <div className="field">
                        <input value={newPlaceForm.contact_info} onChange={(event) => setNewPlaceForm((current) => ({ ...current, contact_info: event.target.value }))} placeholder="Contact info" />
                      </div>
                      <div className="field">
                        <input value={newPlaceForm.website} onChange={(event) => setNewPlaceForm((current) => ({ ...current, website: event.target.value }))} placeholder="Website URL" />
                      </div>
                      <div className="field">
                        <label>Categories</label>
                        <select
                          multiple
                          value={newPlaceForm.category_ids}
                          onChange={(event) => setNewPlaceForm((current) => ({
                            ...current,
                            category_ids: Array.from(event.target.selectedOptions, (option) => option.value),
                          }))}
                        >
                          {bootstrap.categories.map((category) => (
                            <option key={category.CategoryID} value={category.CategoryID}>{category.TagName}</option>
                          ))}
                        </select>
                      </div>
                      <button className="action" type="submit">Create listing</button>
                    </form>
                  </div>
                )}
              </div>
            ) : (
              <form className="form-grid" onSubmit={handleAuthSubmit}>
                {authMode === "register" && (
                  <>
                    <div className="field">
                      <input value={authForm.username} onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))} placeholder="Username" />
                    </div>
                    <div className="field">
                      <input value={authForm.display_name} onChange={(event) => setAuthForm((current) => ({ ...current, display_name: event.target.value }))} placeholder="Display name" />
                    </div>
                    <div className="field">
                      <select value={authForm.role} onChange={(event) => setAuthForm((current) => ({ ...current, role: event.target.value }))}>
                        <option value="tourist">Traveler</option>
                        <option value="business_owner">Business owner</option>
                      </select>
                    </div>
                  </>
                )}
                <div className="field">
                  <input type="email" value={authForm.email} onChange={(event) => setAuthForm((current) => ({ ...current, email: event.target.value }))} placeholder="Email" />
                </div>
                <div className="field">
                  <input type="password" value={authForm.password} onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))} placeholder="Password" />
                </div>
                <button className="action" type="submit">{authMode === "login" ? "Log in" : "Create account"}</button>
              </form>
            )}
          </div>

          <div className="panel">
            <h2 className="section-title">Reviews</h2>
            {session && selectedPlace ? (
              <form className="form-grid" onSubmit={submitReview} style={{ marginTop: 16 }}>
                <div className="field">
                  <select value={reviewForm.rating} onChange={(event) => setReviewForm((current) => ({ ...current, rating: event.target.value }))}>
                    {[5, 4, 3, 2, 1].map((value) => (
                      <option key={value} value={value}>{value} stars</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <input value={reviewForm.title} onChange={(event) => setReviewForm((current) => ({ ...current, title: event.target.value }))} placeholder="Short title" />
                </div>
                <div className="field">
                  <textarea value={reviewForm.body} onChange={(event) => setReviewForm((current) => ({ ...current, body: event.target.value }))} placeholder="What stood out?" />
                </div>
                <div className="split-actions">
                  <button className="action" type="submit">{editingReviewId ? "Update review" : "Post review"}</button>
                  {editingReviewId && (
                    <button className="ghost" type="button" onClick={() => {
                      setEditingReviewId(null);
                      setReviewForm({ rating: "5", title: "", body: "" });
                    }}>
                      Cancel edit
                    </button>
                  )}
                </div>
                {currentUserReview && !editingReviewId && (
                  <div className="subtle">You already reviewed this place. Use Edit below to update it.</div>
                )}
              </form>
            ) : (
              <p className="subtle">Log in to write and manage reviews.</p>
            )}

            <div style={{ marginTop: 18 }}>
              {selectedPlace?.reviews?.length ? selectedPlace.reviews.map((review) => (
                <div className="review" key={review.ReviewID}>
                  <div className="row-between">
                    <div>
                      <strong>{review.Title || "Untitled review"}</strong>
                      <div className="subtle">by {review.DisplayName || review.Username}</div>
                    </div>
                    <div className="badge-row">
                      {session?.role === "admin" && !review.IsVisible && <span className="chip">Hidden</span>}
                      <span className="chip">{review.Rating} / 5</span>
                    </div>
                  </div>
                  <p className="subtle">{review.Body || "No review text."}</p>
                  <div className="review-actions">
                    {session?.user_id === review.UserID && (
                      <>
                        <button className="ghost" onClick={() => beginEditReview(review)}>Edit</button>
                        <button className="danger" onClick={() => deleteReview(review.ReviewID)}>Delete</button>
                      </>
                    )}
                    {session?.role === "admin" && (
                      <button className="ghost" onClick={() => moderateReview(review.ReviewID, !review.IsVisible)}>
                        {review.IsVisible ? "Hide" : "Show"}
                      </button>
                    )}
                  </div>
                </div>
              )) : (
                <div className="empty">No reviews yet for this place.</div>
              )}
            </div>
          </div>

          <div className="panel">
            <h2 className="section-title">Your trip lists</h2>
            {!session && <p className="subtle">Sign in to build and reorder your own itineraries.</p>}
            {session && (
              <div className="stack" style={{ marginTop: 16 }}>
                {ownLists.map((tripList) => (
                  <button className="place-card" key={tripList.ListID} onClick={() => loadOwnLists(tripList.ListID)}>
                    <div className="row-between">
                      <strong>{tripList.Title}</strong>
                      <span className="chip">{tripList.IsPublic ? "Public" : "Private"}</span>
                    </div>
                    <div className="subtle">{tripList.Description || "No description yet."}</div>
                  </button>
                ))}
                {ownLists.length === 0 && <div className="empty">Create your first trip list to start planning.</div>}

                {selectedOwnList && (
                  <div className="list-item">
                    <form className="form-grid" onSubmit={updateList}>
                      <h3 style={{ marginTop: 0 }}>Edit selected trip list</h3>
                      <div className="field">
                        <input value={listEditForm.title} onChange={(event) => setListEditForm((current) => ({ ...current, title: event.target.value }))} />
                      </div>
                      <div className="field">
                        <textarea value={listEditForm.description} onChange={(event) => setListEditForm((current) => ({ ...current, description: event.target.value }))} />
                      </div>
                      <label className="subtle">
                        <input type="checkbox" checked={listEditForm.is_public} onChange={(event) => setListEditForm((current) => ({ ...current, is_public: event.target.checked }))} />{" "}
                        Public list
                      </label>
                      <div className="split-actions">
                        <button className="action" type="submit">Save list</button>
                        <button className="danger" type="button" onClick={deleteList}>Delete list</button>
                      </div>
                    </form>

                    <div className="stack" style={{ marginTop: 18 }}>
                      {selectedOwnList.items.map((item, index) => (
                        <div className="list-item" key={`${item.ListID}-${item.PlaceID}`}>
                          <div className="row-between">
                            <div>
                              <strong>{item.Position}. {item.Name}</strong>
                              <div className="subtle">{item.Address}</div>
                            </div>
                            <button className="danger" onClick={() => removeFromList(item.ListID, item.PlaceID)}>Remove</button>
                          </div>
                          <div className="subtle">{item.Note || "No note added."}</div>
                          <div className="review-actions">
                            <button className="ghost" onClick={() => moveListItem("up", index)}>Move up</button>
                            <button className="ghost" onClick={() => moveListItem("down", index)}>Move down</button>
                          </div>
                        </div>
                      ))}
                      {selectedOwnList.items.length === 0 && <div className="empty">This list is empty.</div>}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {session?.role === "admin" && bootstrap.admin_overview && (
            <div className="panel">
              <h2 className="section-title">Admin moderation</h2>
              <div className="admin-grid">
                <div className="stack">
                  <h3 style={{ marginBottom: 0 }}>Claim requests</h3>
                  {bootstrap.admin_overview.claim_requests.map((claim) => (
                    <div className="list-item" key={claim.ClaimID}>
                      <strong>{claim.PlaceName}</strong>
                      <div className="subtle">{claim.DisplayName} · {claim.Email}</div>
                      <div className="subtle">{claim.Message || "No message provided."}</div>
                      <div className="badge-row">
                        <span className="chip">{claim.Status}</span>
                        {claim.Status === "pending" && (
                          <>
                            <button className="ghost" onClick={() => moderateClaim(claim.ClaimID, "approved")}>Approve</button>
                            <button className="danger" onClick={() => moderateClaim(claim.ClaimID, "rejected")}>Reject</button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="stack">
                  <h3 style={{ marginBottom: 0 }}>Photo queue</h3>
                  {bootstrap.admin_overview.photos.map((photo) => (
                    <div className="list-item" key={photo.PhotoID}>
                      <strong>{photo.PlaceName}</strong>
                      <div className="subtle">{photo.Caption || "No caption"} · {photo.DisplayName}</div>
                      <a href={photo.PhotoURL} target="_blank" rel="noreferrer" className="subtle">{photo.PhotoURL}</a>
                      <div className="badge-row">
                        <span className="chip">{photo.Status}</span>
                        {photo.Status === "pending" && (
                          <>
                            <button className="ghost" onClick={() => moderatePhoto(photo.PhotoID, "approved")}>Approve</button>
                            <button className="danger" onClick={() => moderatePhoto(photo.PhotoID, "rejected")}>Reject</button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="stack">
                  <h3 style={{ marginBottom: 0 }}>Review moderation</h3>
                  {bootstrap.admin_overview.reviews.map((review) => (
                    <div className="list-item" key={review.ReviewID}>
                      <strong>{review.PlaceName}</strong>
                      <div className="subtle">{review.DisplayName} · {review.Rating}/5</div>
                      <div className="subtle">{review.Title || "Untitled review"}</div>
                      <div className="subtle">{review.Body || "No review text."}</div>
                      <div className="badge-row">
                        <span className="chip">{review.IsVisible ? "Visible" : "Hidden"}</span>
                        <button className="ghost" onClick={() => moderateReview(review.ReviewID, !review.IsVisible)}>
                          {review.IsVisible ? "Hide" : "Restore"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="stack">
                  <h3 style={{ marginBottom: 0 }}>Listing visibility</h3>
                  {bootstrap.admin_overview.places.map((place) => (
                    <div className="list-item" key={place.PlaceID}>
                      <strong>{place.Name}</strong>
                      <div className="subtle">{place.Address}</div>
                      <div className="badge-row">
                        <span className="chip">{place.IsActive ? "Visible" : "Hidden"}</span>
                        <button className="ghost" onClick={() => moderatePlace(place.PlaceID, !place.IsActive)}>
                          {place.IsActive ? "Hide listing" : "Restore listing"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);

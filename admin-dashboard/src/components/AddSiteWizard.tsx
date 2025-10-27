import { useState, useEffect, FormEvent } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import { LatLng } from 'leaflet';
import { X, MapPin, Search, ImageIcon, FileText, Loader2, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { placesApi, sitesApi, toursApi, adminAiApi } from '../lib/api';
import type { PlaceSearchResult, PlaceDetails, PlacePhoto, Site } from '../types';

interface AddSiteWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSiteCreated: (site: Site) => void;
  tourId?: string;
  initialLocation?: { latitude: number; longitude: number };
}

// Helper component to handle map clicks
function MapClickHandler({ onLocationSelect }: { onLocationSelect: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Helper component to recenter map
function MapRecenter({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);
  return null;
}

type WizardStep = 'location' | 'search' | 'photos' | 'details';

export default function AddSiteWizard({ isOpen, onClose, onSiteCreated, tourId, initialLocation }: AddSiteWizardProps) {
  const [step, setStep] = useState<WizardStep>('location');
  const [siteName, setSiteName] = useState('');
  const [location, setLocation] = useState<{ latitude: number; longitude: number }>(
    initialLocation || { latitude: 40.7580, longitude: -73.9855 } // Times Square default
  );
  const [searchResults, setSearchResults] = useState<PlaceSearchResult[]>([]);
  const [selectedPlace, setSelectedPlace] = useState<PlaceDetails | null>(null);
  const [selectedPhoto, setSelectedPhoto] = useState<PlacePhoto | null>(null);
  const [description, setDescription] = useState('');
  const [city, setCity] = useState('');
  const [neighborhood, setNeighborhood] = useState('');
  const [searching, setSearching] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generatingDescription, setGeneratingDescription] = useState(false);

  // Reset state when wizard opens
  useEffect(() => {
    if (isOpen) {
      setStep('location');
      setSiteName('');
      setLocation(initialLocation || { latitude: 40.7580, longitude: -73.9855 });
      setSearchResults([]);
      setSelectedPlace(null);
      setSelectedPhoto(null);
      setDescription('');
      setCity('');
      setNeighborhood('');
    }
  }, [isOpen, initialLocation]);

  const handleSearchPlaces = async () => {
    if (!siteName.trim()) {
      toast.error('Please enter a site name');
      return;
    }

    setSearching(true);
    try {
      const response = await placesApi.search(siteName, location.latitude, location.longitude, 5000);
      setSearchResults(response.results);
      if (response.results.length === 0) {
        toast.error('No places found. Try a different search term or location.');
      } else {
        setStep('search');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to search places');
    } finally {
      setSearching(false);
    }
  };

  const handleSelectPlace = async (place: PlaceSearchResult) => {
    setLoadingDetails(true);
    try {
      const details = await placesApi.getDetails(place.placeId);
      setSelectedPlace(details);
      setSiteName(details.name);
      setLocation({
        latitude: details.location.latitude,
        longitude: details.location.longitude,
      });
      setDescription(details.editorialSummary || '');

      // Generate AI description in background
      setGeneratingDescription(true);
      adminAiApi.generateDescription({
        siteName: details.name,
        latitude: details.location.latitude,
        longitude: details.location.longitude,
      }).then((result) => {
        setDescription(result.description);
        setGeneratingDescription(false);
        toast.success('AI description generated!');
      }).catch((error) => {
        console.error('Failed to generate description:', error);
        setGeneratingDescription(false);
        // Keep the editorial summary if AI generation fails
        if (!description) {
          setDescription(details.editorialSummary || '');
        }
      });

      if (details.photos.length > 0) {
        setStep('photos');
      } else {
        toast.error('No photos available for this place');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to get place details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleSelectPhoto = (photo: PlacePhoto) => {
    setSelectedPhoto(photo);
    setStep('details');
  };

  const handleSave = async () => {
    if (!siteName.trim()) {
      toast.error('Site name is required');
      return;
    }
    if (!selectedPlace) {
      toast.error('Please select a place from search results');
      return;
    }
    if (!selectedPhoto) {
      toast.error('Please select a photo');
      return;
    }

    setSaving(true);
    try {
      // Photo is already in S3 from the details endpoint
      // Create the site
      const siteData: Partial<Site> = {
        title: siteName,
        description: description.trim() || selectedPlace.editorialSummary || '',
        latitude: location.latitude,
        longitude: location.longitude,
        city: city.trim() || null,
        neighborhood: neighborhood.trim() || null,
        imageUrl: selectedPhoto.url,  // Already uploaded to S3 (raw URL)
        placeId: selectedPlace.placeId,
        formatted_address: selectedPlace.formattedAddress,
        types: selectedPlace.types,
        user_ratings_total: selectedPlace.userRatingsTotal,
        phone_number: selectedPlace.phoneNumber,
        webUrl: selectedPlace.website,
        rating: selectedPlace.rating,
        googlePhotoReferences: selectedPlace.photos.map((p) => p.url),  // S3 URLs of all photos
      };

      const newSite = await sitesApi.create(siteData);

      // If creating from tour context, add the site to the tour
      if (tourId) {
        // Fetch current tour to get existing site IDs
        const currentTour = await toursApi.get(tourId);
        const existingSiteIds = currentTour.siteIds || [];

        // Add new site to the tour
        await toursApi.update(tourId, {
          siteIds: [...existingSiteIds, newSite.id],
        });
      }

      toast.success('Site created successfully!');
      onSiteCreated(newSite);
      onClose();
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to create site');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">
            Add New Site {tourId && '(to Tour)'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center px-6 py-4 border-b bg-gray-50">
          <div className="flex items-center space-x-2">
            <div className={`flex items-center space-x-2 ${step === 'location' ? 'text-blue-600' : 'text-gray-400'}`}>
              <MapPin className="w-5 h-5" />
              <span className="text-sm font-medium">Location</span>
            </div>
            <div className="w-8 h-px bg-gray-300" />
            <div className={`flex items-center space-x-2 ${step === 'search' ? 'text-blue-600' : 'text-gray-400'}`}>
              <Search className="w-5 h-5" />
              <span className="text-sm font-medium">Search</span>
            </div>
            <div className="w-8 h-px bg-gray-300" />
            <div className={`flex items-center space-x-2 ${step === 'photos' ? 'text-blue-600' : 'text-gray-400'}`}>
              <ImageIcon className="w-5 h-5" />
              <span className="text-sm font-medium">Photo</span>
            </div>
            <div className="w-8 h-px bg-gray-300" />
            <div className={`flex items-center space-x-2 ${step === 'details' ? 'text-blue-600' : 'text-gray-400'}`}>
              <FileText className="w-5 h-5" />
              <span className="text-sm font-medium">Details</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: Location */}
          {step === 'location' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Site Name
                </label>
                <input
                  type="text"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  placeholder="e.g., Statue of Liberty"
                  className="w-full px-3 py-2 border rounded-md"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location (click on map to adjust)
                </label>
                <div className="h-96 rounded-md overflow-hidden border">
                  <MapContainer
                    center={[location.latitude, location.longitude]}
                    zoom={16}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[location.latitude, location.longitude]} />
                    <MapRecenter center={[location.latitude, location.longitude]} />
                    <MapClickHandler
                      onLocationSelect={(lat, lng) => setLocation({ latitude: lat, longitude: lng })}
                    />
                  </MapContainer>
                </div>
                <p className="text-sm text-gray-500 mt-2">
                  Lat: {location.latitude.toFixed(6)}, Lng: {location.longitude.toFixed(6)}
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Search Results */}
          {step === 'search' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Select Place</h3>
                <button
                  onClick={() => setStep('location')}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  ← Back to Location
                </button>
              </div>

              {loadingDetails && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
              )}

              {!loadingDetails && (
                <div className="space-y-2">
                  {searchResults.map((place) => (
                    <button
                      key={place.placeId}
                      onClick={() => handleSelectPlace(place)}
                      className="w-full text-left p-4 border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition"
                    >
                      <h4 className="font-medium">{place.name}</h4>
                      <p className="text-sm text-gray-600">{place.formattedAddress}</p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        {place.rating && (
                          <span>⭐ {place.rating}</span>
                        )}
                        {place.userRatingsTotal && (
                          <span>({place.userRatingsTotal} reviews)</span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Photo Selection */}
          {step === 'photos' && selectedPlace && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Select Photo</h3>
                <button
                  onClick={() => setStep('search')}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  ← Back to Search
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {selectedPlace.photos.map((photo, index) => (
                  <button
                    key={index}
                    onClick={() => handleSelectPhoto(photo)}
                    className={`relative aspect-video rounded-lg overflow-hidden border-2 transition ${
                      selectedPhoto?.photoReference === photo.photoReference
                        ? 'border-blue-500 ring-2 ring-blue-200'
                        : 'border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <img
                      src={photo.presignedUrl}
                      alt={`Photo ${index + 1}`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const img = e.target as HTMLImageElement;
                        img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle"%3ENo Image%3C/text%3E%3C/svg%3E';
                      }}
                    />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Details */}
          {step === 'details' && selectedPlace && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Site Details</h3>
                <button
                  onClick={() => setStep('photos')}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  ← Back to Photos
                </button>
              </div>

              {selectedPhoto && (
                <div className="aspect-video rounded-lg overflow-hidden border">
                  <img
                    src={selectedPhoto.presignedUrl}
                    alt="Selected"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Site Name
                </label>
                <input
                  type="text"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center justify-between">
                  <span>Description</span>
                  {generatingDescription && (
                    <span className="text-xs text-blue-600 flex items-center space-x-1">
                      <Sparkles className="w-3 h-3 animate-pulse" />
                      <span>Generating with AI...</span>
                    </span>
                  )}
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={generatingDescription ? "AI is generating a description..." : "Enter site description..."}
                  className="w-full px-3 py-2 border rounded-md h-32 resize-none"
                  disabled={generatingDescription}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {generatingDescription
                    ? 'Please wait while AI generates a description. You can edit it afterwards.'
                    : 'AI-generated description. You can edit this now or later if needed.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="e.g., New York"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Neighborhood
                  </label>
                  <input
                    type="text"
                    value={neighborhood}
                    onChange={(e) => setNeighborhood(e.target.value)}
                    placeholder="e.g., Williamsburg"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
                <div>
                  <span className="font-medium">Address:</span> {selectedPlace.formattedAddress}
                </div>
                {selectedPlace.phoneNumber && (
                  <div>
                    <span className="font-medium">Phone:</span> {selectedPlace.phoneNumber}
                  </div>
                )}
                {selectedPlace.website && (
                  <div>
                    <span className="font-medium">Website:</span>{' '}
                    <a href={selectedPlace.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {selectedPlace.website}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-md transition"
          >
            Cancel
          </button>

          <div className="flex items-center space-x-2">
            {step === 'location' && (
              <button
                onClick={handleSearchPlaces}
                disabled={searching || !siteName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition flex items-center space-x-2"
              >
                {searching ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    <span>Search Places</span>
                  </>
                )}
              </button>
            )}

            {step === 'photos' && (
              <button
                onClick={() => selectedPhoto && setStep('details')}
                disabled={!selectedPhoto}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
              >
                Continue
              </button>
            )}

            {step === 'details' && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition flex items-center space-x-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Site...</span>
                  </>
                ) : (
                  <span>Create Site</span>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

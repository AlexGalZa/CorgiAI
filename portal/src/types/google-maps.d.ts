// Minimal type declarations for Google Maps Places API.
// Install @types/google.maps for full types: npm install --save-dev @types/google.maps

declare namespace google {
  namespace maps {
    namespace places {
      class Autocomplete {
        constructor(
          input: HTMLInputElement,
          opts?: { types?: string[]; componentRestrictions?: { country: string | string[] } }
        );
        addListener(event: string, handler: () => void): void;
        getPlace(): PlaceResult;
      }

      interface PlaceResult {
        formatted_address?: string;
        address_components?: AddressComponent[];
      }

      interface AddressComponent {
        long_name: string;
        short_name: string;
        types: string[];
      }
    }

    namespace event {
      function clearInstanceListeners(instance: object): void;
    }
  }
}

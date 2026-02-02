interface CountryFlagProps {
  country: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const FLAG_CODES: Record<string, string> = {
  Ireland: 'ie',
  England: 'gb-eng',
  France: 'fr',
  Wales: 'gb-wls',
  Scotland: 'gb-sct',
  Italy: 'it',
};

const SIZES = {
  sm: { width: 20, height: 15 },
  md: { width: 24, height: 18 },
  lg: { width: 32, height: 24 },
};

export function CountryFlag({ country, size = 'md', className = '' }: CountryFlagProps) {
  const code = FLAG_CODES[country];
  const { width, height } = SIZES[size];

  if (!code) {
    return <span className={className}>{country}</span>;
  }

  // Using flagcdn.com for high-quality flag images
  // Sub-national codes (gb-eng, gb-wls, gb-sct) require {w}x{h} format, not w{n}
  const retinaW = width * 2;
  const retinaH = height * 2;
  const url = `https://flagcdn.com/${retinaW}x${retinaH}/${code}.png`;

  return (
    <img
      src={url}
      alt={`${country} flag`}
      width={width}
      height={height}
      className={`inline-block object-cover ${className}`}
      style={{ borderRadius: '2px' }}
    />
  );
}

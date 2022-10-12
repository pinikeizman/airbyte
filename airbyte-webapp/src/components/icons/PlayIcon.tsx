interface Props {
  color?: string;
}

const PlayIcon = ({ color = "currentColor" }: Props): JSX.Element => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" role="img" data-icon="play">
    <path
      d="M0 0.993C0 0.445 0.445 0 0.993 0H17.007C17.555 0 18 0.445 18 0.993V17.007C17.9997 17.2703 17.895 17.5227 17.7089 17.7089C17.5227 17.895 17.2703 17.9997 17.007 18H0.993C0.729721 17.9997 0.477302 17.895 0.291135 17.7089C0.104969 17.5227 0.000264735 17.2703 0 17.007V0.993ZM2 2V16H16V2H2ZM7.622 5.415L12.501 8.667C12.5559 8.70351 12.6009 8.75302 12.632 8.81111C12.6631 8.86921 12.6794 8.93409 12.6794 9C12.6794 9.06591 12.6631 9.13079 12.632 9.18889C12.6009 9.24698 12.5559 9.29649 12.501 9.333L7.621 12.585C7.56083 12.6249 7.49098 12.6477 7.41887 12.6512C7.34676 12.6546 7.27507 12.6384 7.21141 12.6043C7.14774 12.5703 7.09448 12.5197 7.05726 12.4578C7.02004 12.396 7.00025 12.3252 7 12.253V5.747C7.00013 5.67465 7.01989 5.60369 7.05716 5.54168C7.09443 5.47967 7.14782 5.42893 7.21165 5.39486C7.27547 5.36079 7.34734 5.34467 7.41961 5.34822C7.49187 5.35177 7.56182 5.37485 7.622 5.415V5.415Z"
      fill={color}
    />
  </svg>
);

export default PlayIcon;
